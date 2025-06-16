from pathlib import Path


def make_registry(base, dirs, output, recursive=True):
    from pooch import file_hash
    pat = '**/*' if recursive else '*'
    hashes = {p.relative_to(base).as_posix(): file_hash(str(p)) for d in dirs for p in base.joinpath(d).glob(pat) if p.is_file()}
    names = sorted(hashes.keys())
    with open(output, 'w') as outfile:
        for name in names:
            outfile.write(f'{name} {hashes[name]}\n')


def make_registries(repo, base, message):
    registries = {
        'a': ('a', 'A',),
        'b': ('b', 'B',),
        'c': ('c/A', 'c/B', 'c/C'),
    }
    for name, dirs in registries.items():
        registry_name = f'{name}-registry.txt'
        make_registry(base, dirs, registry_name)
        repo.git.add(registry_name)
    repo.index.commit(message)


def one_tag(repo, base, source, tag):
    source_current = source.active_branch
    repo_current = repo.active_branch

    source.git.checkout(tag)
    message = f'Add {tag} registries'
    make_registries(repo, base, message)
    repo.create_tag(tag, message=message)

    source.git.checkout(source_current.name)
    repo.git.checkout(repo_current.name)


def v_tags(repo):
    return [tag for tag in repo.tags if str(tag).startswith('v')]


def do_everything(repo, parent, source, tag: str):
    source_tags = [tag] if tag else v_tags(source)
    repo_tags =  v_tags(repo)
    missing = [t for t in source_tags if t not in repo_tags]
    # missing holds source-defined tag(s) that this repo does not have
    for tag in missing:
        print(f'Handle missing {tag=}')
        one_tag(repo, parent, source, tag)
    return len(missing) > 0


def main(parent: Path, push: bool, remove: bool, tag: str):
    import git
    repo = git.Repo(Path(__file__).parent, search_parent_directories=False)
    changed = False
    if remove and tag in repo.refs:
        repo.delete_tag(tag)
        if push:
            print(f'Push removed tag {tag} to origin')
            repo.remote('origin').push(refspec=f':{tag}')
    elif not remove:
        source = git.Repo(parent, search_parent_directories=False)
        if do_everything(repo, parent, source, tag) and push:
            print(f'Push tags to origin')
            repo.remote('origin').push(tags=True)
        

if __name__ == '__main__':
    from argparse import ArgumentParser
    from pathlib import Path
    parser = ArgumentParser('register')
    parser.add_argument('-n', '--no-push', action='store_true', default=False)
    parser.add_argument('--parent', type=str, default=None, help='Parent repository directory to register')
    parser.add_argument('--remove', type=int, nargs='?', help='Remove the specified tag, otherwise add/update')
    parser.add_argument('tag', type=str, nargs='?', help='Add/update/remove this tag, or Add missing tags if empty')
    args = parser.parse_args()

    if args.parent is None:
        raise ValueError("The parent directory must be defined")
    parent = Path(args.parent)
    if not parent.is_dir():
        raise ValueError(f"The parent directory {parent} must exist")

    remove = args.remove or 0
    if args.tag is None and remove != 0:
        raise ValueError(f'Non-zero {remove=} without a specified tag is not allowed')

    main(parent=parent, push=not args.no_push, remove=remove, tag=args.tag or '')
    
