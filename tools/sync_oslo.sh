#!/bin/bash -e

OSLO_DIR=../oslo-incubator
SYNC_DIR=keystone/openstack/common
SYNC_REF_FILE=$SYNC_DIR/CURRENT_SYNC_REF

die() {
    echo $@ >&2
    exit 1
}

# Get the ref from the last sync
if [ ! -e "$SYNC_REF_FILE" ]; then
    die "$SYNC_REF_FILE does not exist; please add it manually"
fi
current_ref=`cat $SYNC_REF_FILE`

# Clean out the currently synced files. This will allows deletions to occur.
rm -r $SYNC_DIR

# Do the sync
(cd $OSLO_DIR; python update.py ../keystone) > /dev/null
changed_files=`git status --short | grep '^ [MD]' | sed 's/.*keystone\///'`

# Restore the README
git checkout $SYNC_DIR/README

# Get a list of oslo diffs
diffs=$(cd $OSLO_DIR;
        git log --pretty=oneline --abbrev-commit $current_ref..HEAD -- $changed_files)
if [ -z "$diffs" ]; then
    die "no changes to commit"
fi

# Get the current oslo ref
new_ref=$(cd ../oslo-incubator; git rev-parse --short HEAD)

# Save the current oslo ref for later
echo $new_ref > $SYNC_DIR/CURRENT_SYNC_REF

# Commit the changes
commit_message="Sync with oslo-incubator $new_ref

Commits
-------
$diffs
"
git add keystone/openstack -A
git commit -m "$commit_message"
