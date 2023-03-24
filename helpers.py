"""Helper functions."""
try:
    from selinux import selinux_check_access as check_access
except ImportError:
    pass


def construct_selinux_context(
    selinux_user: str,
    selinux_role: str,
    selinux_type: str,
    selinux_sensitivity: str,
    selinux_category: str,
) -> str:
    """Return SELinux context as string from its parts."""
    context = [selinux_user, selinux_role, selinux_type, selinux_sensitivity]
    if selinux_category is not None:
        context.append(selinux_category)
    return ':'.join(context)


def selinux_check_access(scon, tcon, tclass, perm):
    code = {0: 1}
    try:
        ret = check_access(scon, tcon, tclass, perm)
    except PermissionError:
        return 0
    return code.get(ret, 0)
