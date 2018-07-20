set -euo pipefail
function fetch() {
	curl --header "Private-Token: $GITLAB_API_TOKEN" https://gitlab.com/api/v4/projects/cloudigrade%2Fintegrade/pipelines?status=running 2>/dev/null | python -m json.tool | grep '"ref": ' | grep -v $CI_COMMIT_REF_NAME || true
	return 0
}
RUNNING="$(fetch)"
if [[ "$RUNNING" != "" ]]; then
	echo -en "Pipeline busy. Waiting"
fi
while [[ "$RUNNING" != "" ]]; do
	echo -en "."
	sleep 60
	RUNNING=$(fetch)
done
echo
exit 0