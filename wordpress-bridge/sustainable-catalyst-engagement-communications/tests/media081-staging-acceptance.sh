#!/bin/bash
# MEDIA-08.1 staging acceptance. DISPOSABLE STAGING ONLY, never production.
#   bash media081-staging-acceptance.sh <wordpress-path> <site-url>
# Requires: the 8.9.5 plugin active, an administrator `staging-admin`, permalinks on.
# Creates a local test reviewer, toggles the staging flag/page between phases and
# checks anonymous HTTP behaviour. Leaves the flag OFF at the end.
set -uo pipefail
WP=${1:?wordpress path}; URL=${2:?site url}; URL=${URL%/}
HERE=$(cd "$(dirname "$0")" && pwd); T=$HERE/media081-wp-acceptance.php
export MEDIA081_STATE=$(mktemp); trap 'rm -f "$MEDIA081_STATE"' EXIT
w() { wp --path="$WP" "$@"; }
[ "$(w eval 'echo wp_get_environment_type();')" = production ] && { echo "refused: production"; exit 2; }
pass=0; fail=0
ok() { if eval "$2"; then echo "PASS $1"; pass=$((pass+1)); else echo "FAIL $1"; fail=$((fail+1)); fi; }
phase() { w eval-file "$T" "$1" | tee /dev/stderr | grep -q "fail=0" && pass=$((pass+1)) || fail=$((fail+1)); }
get() { curl -s -o /tmp/media081-body.$$ -w '%{http_code}' "$1"; }
has() { grep "$@" /tmp/media081-body.$$; }
st() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2],""))' "$MEDIA081_STATE" "$1"; }

w config delete SCEC_MEDIA08_PUBLIC_RELEASE >/dev/null 2>&1
w config delete SCEC_MEDIA08_SINGLE_OPERATOR_OWNER >/dev/null 2>&1
w user get press-reviewer >/dev/null 2>&1 || w user create press-reviewer press-reviewer@example.invalid --role=scec_press_reviewer \
  --user_pass="$(python3 -c 'import secrets;print(secrets.token_urlsafe(18))')" --quiet
for id in $(w post list --name=press --post_type=page --format=ids); do w post delete "$id" --force --quiet; done

echo "== phase private (flag off, no /press/ page)"; phase private
ok "anonymous /press/ is 404 before the page exists" '[ "$(get $URL/press/)" = 404 ]'
ok "anonymous release route is 404 before launch" '[ "$(get $URL/press/$(date -u +%Y)/synthetic-first-release/)" = 404 ]'
ok "press sitemap 404 before launch" '[ "$(get $URL/press/sitemap.xml)" = 404 ]'

w post create --post_type=page --post_status=publish --post_title=Press --post_name=press --post_content='[sc_press_room]' --quiet
echo "== phase gated (/press/ published, flag off)"; phase gated
ok "/press/ page renders with no releases" '[ "$(get $URL/press/)" = 200 ] && has -q "No approved public press releases"'

w config set SCEC_MEDIA08_PUBLIC_RELEASE true --raw --type=constant --quiet; sleep 3
echo "== phase public (flag on)"; phase public
F=$(st first_url); C=$(st correction_url)
ok "release page 200 at its permanent URL" '[ "$(get $F)" = 200 ]'
ok "title tag is the headline" 'has -q "<title>SYNTHETIC first release | Press |"'
ok "canonical is the permanent URL" 'has -qi "rel=\"canonical\" href=\"$F\""'
ok "robots index (not noindex)" 'has -qiE "name=\"robots\" content=\"index"'
ok "NewsArticle JSON-LD" 'has -q "\"@type\":\"NewsArticle\""'
ok "correction notice on the original" 'has -q "Correction issued"'
ok "original text unchanged" 'has -q "SYNTHETIC staging body"'
ok "content fingerprint shown" 'has -q "Content fingerprint (SHA-256)"'
ok "withdrawn correction keeps a notice (200)" '[ "$(get $C)" = 200 ] && has -q "This release was withdrawn on"'
ok "withdrawn page is noindex" 'has -qiE "name=\"robots\" content=\"[^\"]*noindex"'
ok "withdrawn page hides the body" '! has -q "SYNTHETIC corrected body"'
ok "Press Room lists the release with its URL" '[ "$(get $URL/press/)" = 200 ] && has -q "$F"'
ok "embargoed release not listed" '! has -q "SYNTHETIC embargoed release"'
ok "Media page links Press & News to /press/" '[ "$(get $URL/media/)" = 200 ] && has -q "href=\"$URL/press/\""'
ok "press sitemap lists the release, not the withdrawn one" '[ "$(get $URL/press/sitemap.xml)" = 200 ] && has -q "$F" && ! has -q "$C"'
ok "sitemap index references the press sitemap" '[ "$(get $URL/sitemap_index.xml)" = 200 ] && has -q "press/sitemap.xml"'
ok "unknown release slug 404" '[ "$(get $URL/press/2026/no-such-release/)" = 404 ]'
ok "private record not reachable by id" '[ "$(get "$URL/?p=$(st first)")" = 404 ]'
ok "no REST exposure" '[ "$(get $URL/wp-json/wp/v2/scec_press_release)" = 404 ]'

w user get staging-admin2 >/dev/null 2>&1 || w user create staging-admin2 staging-admin2@example.invalid --role=administrator \
  --user_pass="$(python3 -c 'import secrets;print(secrets.token_urlsafe(18))')" --quiet
OWNER=$(w user get staging-admin --field=ID)
w config set SCEC_MEDIA08_SINGLE_OPERATOR_OWNER "$OWNER" --raw --type=constant --quiet; sleep 3
echo "== phase single (owner self-review)"; phase single
O=$(st owner_url)
ok "owner release page 200" '[ "$(get $O)" = 200 ]'
ok "owner release discloses self-review" 'has -q "not independent review" && has -q "self-reviewed, not independently reviewed"'
ok "owner release not labelled independent" '! has -q "Approved by an independent reviewer"'
ok "owner release canonical and NewsArticle" 'has -qi "rel=\"canonical\" href=\"$O\"" && has -q "\"@type\":\"NewsArticle\""'
ok "press sitemap lists owner release" '[ "$(get $URL/press/sitemap.xml)" = 200 ] && has -q "$O"'
w config set SCEC_MEDIA08_SINGLE_OPERATOR_OWNER "$(w user get press-reviewer --field=ID)" --raw --type=constant --quiet; sleep 3
echo "== phase single_off (owner = non-administrator)"; phase single_off
w config delete SCEC_MEDIA08_SINGLE_OPERATOR_OWNER --quiet; sleep 3
echo "== phase single_off (owner constant removed)"; phase single_off
ok "owner release still public with the mode off" '[ "$(get $O)" = 200 ]'

echo "== phase tamper"; phase tamper
w config set SCEC_MEDIA08_PUBLIC_RELEASE false --raw --type=constant --quiet; sleep 3
echo "== phase killswitch (flag off)"; phase killswitch
ok "release URL 404 when the flag is off" '[ "$(get $F)" = 404 ]'
ok "press sitemap 404 when the flag is off" '[ "$(get $URL/press/sitemap.xml)" = 404 ]'
ok "sitemap index no longer references it" '! { get $URL/sitemap_index.xml >/dev/null; has -q press-sitemap; }'
w config delete SCEC_MEDIA08_PUBLIC_RELEASE --quiet
rm -f /tmp/media081-body.$$
echo "RESULT staging acceptance pass=$pass fail=$fail"
[ "$fail" = 0 ]
