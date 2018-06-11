oc rsh -c postgresql $(oc get pods -o jsonpath='{.items[*].metadata.name}' -l name=postgresql) scl enable rh-postgresql96 -- psql -d cloudigrade -c 'truncate account_account cascade;'
