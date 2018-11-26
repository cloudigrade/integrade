oc rsh -c c-review-502-add-instance-vcpu-memory-a $(oc get pods -o jsonpath='{.items[*].metadata.name}' -l name=c-review-502-add-instance-vcpu-memory-a) scl enable rh-python36 -- python manage.py $*
