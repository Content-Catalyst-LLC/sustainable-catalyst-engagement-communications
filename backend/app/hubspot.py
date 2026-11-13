"""Optional, explicit contact/company export. No newsletter or research mapping."""
from dataclasses import dataclass
import httpx

SCOPES = ('crm.objects.contacts.read', 'crm.objects.contacts.write',
          'crm.objects.companies.read', 'crm.objects.companies.write')

@dataclass(frozen=True)
class SyncResult:
    state: str
    provider_id: str | None = None
    retryable: bool = False

class HubSpot:
    def __init__(self, token: str, *, transport=None):
        if not token or '\n' in token or '\r' in token:
            raise ValueError('Backend credential required')
        self.client = httpx.Client(base_url='https://api.hubapi.com',
            headers={'Authorization': 'Bearer ' + token}, timeout=8,
            follow_redirects=False, transport=transport)

    def close(self):
        self.client.close()

    def sync(self, kind: str, properties: dict, *, approved: bool) -> SyncResult:
        if not approved:
            return SyncResult('not_approved')
        fields = {'contacts': {'email', 'firstname', 'lastname'},
                  'companies': {'domain', 'name'}}
        key = {'contacts': 'email', 'companies': 'domain'}.get(kind)
        if key is None or not properties or set(properties) - fields[kind] or not properties.get(key) or any(not isinstance(v,str) or not v.strip() or len(v)>254 for v in properties.values()):
            return SyncResult('invalid_mapping')
        # Search before creation; 409 is retried by searching again. Never
        # blindly retry a timed-out create, since the provider may have saved it.
        try:
            response = self.client.post(f'/crm/v3/objects/{kind}/search', json={
                'filterGroups': [{'filters': [{'propertyName': key, 'operator': 'EQ',
                                              'value': properties[key].casefold()}]}], 'limit': 2})
            if response.status_code != 200:
                return self.failure(response)
            matches = response.json()['results']
            if len(matches) > 1:
                return SyncResult('ambiguous_match')
            if matches:
                ident = str(matches[0]['id'])
                if not ident.isdigit():
                    return SyncResult('invalid_response')
                response = self.client.patch(f'/crm/v3/objects/{kind}/{ident}',
                                              json={'properties': properties})
            else:
                response = self.client.post(f'/crm/v3/objects/{kind}', json={'properties': properties})
            if response.status_code not in (200, 201):
                return self.failure(response)
            ident = str(response.json()['id'])
            return SyncResult('synced', ident) if ident.isdigit() else SyncResult('invalid_response')
        except httpx.HTTPError:
            return SyncResult('transport_error', retryable=True)
        except (ValueError, KeyError, TypeError):
            return SyncResult('invalid_response')

    @staticmethod
    def failure(response):
        code = response.status_code
        return SyncResult('unauthorized' if code in (401, 403) else
                          'conflict' if code == 409 else
                          'rate_limited' if code == 429 else 'provider_error',
                          retryable=code in (409, 429) or code >= 500)
