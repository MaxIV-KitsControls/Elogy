import pwd
import grp

from flask import current_app
from flask_restful import Resource, marshal_with, reqparse
try:
    import ldap
except ImportError:
    ldap = None

from . import fields


users_parser = reqparse.RequestParser()
users_parser.add_argument("search", type=str, default="")
users_parser.add_argument("groups", type=str, default="")


def search_ldap(server, basedn, search):
    l = ldap.open(server)

    # approximate match against login OR full name
    search_user = "(|(uid~={search}*)(cn~={search}))".format(search=search)

    ldap_attributes = ["uid", "cn", "mail"]
    attributes = ["login", "name", "email"]
    resid = l.search(basedn, ldap.SCOPE_SUBTREE, search_user,
                     ldap_attributes)

    results = []
    while True:
        result_type, result_data = l.result(resid, 0)
        if (result_data == []):
            break
        else:
            if result_type == ldap.RES_SEARCH_ENTRY:
                results.append(dict(zip(attributes, result_data)))
    l.unbind_s()  # disconnect
    return results


class GroupDoesNotExist(Exception):
    pass


class UsersResource(Resource):

    """
    Note: The list of users is just taken from the underlying
    system. Elogy does not really know or care where users come from,
    it just stores the authors as a list of arbitrary strings. This
    is intended as a convenient way to find user names.

    search: arbitrary string that will be matched against logins and
            full names
    groups: a list of group names to restrict the search to.
    """

    @marshal_with(fields.user, envelope="users")
    def get(self):

        args = users_parser.parse_args()
        search = args.get("search", "")

        # if LDAP is configured, let's check that
        LDAP_SERVER = current_app.config.get("LDAP_SERVER")
        LDAP_BASEDN = current_app.config.get("LDAP_BASEDN")
        if LDAP_SERVER and LDAP_BASEDN:
            return search_ldap(LDAP_SERVER, LDAP_BASEDN, search)

        # otherwise check for local users
        groups = args.get("groups", [])
        if groups:
            groups = groups.split(",")
        candidates = []
        try:
            grp_filter = [grp.getgrnam(group) for group in groups]
        except KeyError:
            raise GroupDoesNotExist
        gids = [g.gr_gid for g in grp_filter]
        # This is a little fiddly; in order to get all users from
        # the given groups we need to both theck if the user has
        # the group as "primary group", or if the user is otherwise
        # a member.
        users = set(u for u in pwd.getpwall()
                    if gids and u.pw_gid in gids or
                    all(u.pw_name in g.gr_mem for g in grp_filter))
        for u in users:
            full_name = u.pw_gecos.strip(" ,")
            if (u.pw_name.startswith(search) or search in full_name.lower()):
                candidates.append({
                    "login": u.pw_name, "name": full_name
                })
        return candidates
