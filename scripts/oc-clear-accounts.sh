#!/usr/bin/env bash

cat << EOF | ./scripts/oc-manage.sh shell
from account.models import Account
count, _ = Account.objects.all().delete()
print("Deleted %d Accounts." % (count,))
EOF