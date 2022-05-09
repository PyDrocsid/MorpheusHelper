#!/bin/bash

# install via ./pre-commit.sh install

SELF=$(realpath $0)
SRC=$(realpath pre-commit.sh)
_HOOK=$(git rev-parse --git-path hooks)/pre-commit
HOOK=$(realpath $_HOOK)

install() {
    echo Installing pre-commit hook...
    rm -f $_HOOK
    cp $SRC $HOOK && chmod +x $HOOK && echo Pre-Commit hook has been installed successfully!
}

uninstall() {
    echo Uninstalling pre-commit hook...
    rm -f $_HOOK && echo Pre-Commit hook has been uninstalled successfully!
}

save() {
    git submodule foreach "git name-rev --name-only --always --exclude='tags/*' HEAD > .head.ref && /bin/bash $SELF save" && git submodule update

    git diff > .unstaged.patch
    git diff --staged > .staged.patch
    git restore -WS .
}

restore() {
    git submodule foreach "git restore . && git checkout \$(cat .head.ref) && rm .head.ref && /bin/bash $SELF restore"

    git apply -3 --allow-empty .staged.patch && rm .staged.patch || echo "Warning: Could not restore staged changes in $(pwd)"
    git apply --allow-empty .unstaged.patch && rm .unstaged.patch || echo "Warning: Could not restore unstaged changes in $(pwd)"
}

if [[ "$1" =~ ^(install|uninstall|save|restore)$ ]]; then
    $1
    exit $?
fi

if ! cmp -s $SRC $HOOK; then
    set -e
    echo Updating pre-commit hook...
    rm -f $_HOOK
    cp $SRC $HOOK && chmod +x $HOOK && echo Pre-Commit hook has been updated successfully!
    /bin/bash $HOOK "$@"
    exit $?
elif [[ "$SELF" != "$HOOK" ]]; then
    /bin/bash $HOOK "$@"
    exit $?
fi

save
git apply --allow-empty --index .staged.patch && rm .staged.patch && touch .staged.patch
git add -u

$HOME/.local/bin/poe pre-commit
code=$?

git add -u

restore

exit $code
