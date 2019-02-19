import pwd
import grp

from flask import current_app
from flask_restful import Resource, marshal_with, reqparse
try:
    import ldap
except ImportError:
    ldap = None

from . import fields


def search_ldap(server, basedn, search, max_results=20):

    "Search the ldap server for a user"
    

    l = ldap.initialize("ldap://" + server)


    LDAP_BIND_USERNAME = current_app.config.get("LDAP_BIND_USERNAME")
    LDAP_BIND_PASSWORD = current_app.config.get("LDAP_BIND_PASSWORD")

    # Some ldap connections requires a bind user to search, check if that's the case
    if LDAP_BIND_USERNAME and LDAP_BIND_PASSWORD:
        l.set_option(ldap.OPT_REFERRALS, 0)
        l.bind_s(LDAP_BIND_USERNAME, LDAP_BIND_PASSWORD)

    # partial match against full name OR login
    if search:
        search_user = "(|(cn=*{search}*)(sAMAccountName=*{search}*))".format(search=search)
    else:
        search_user = "cn=*"

    ldap_attributes = ["sAMAccountName", "cn", "mail"]
    attributes = ["login", "name", "email"]
    results = l.search_s(basedn, ldap.SCOPE_SUBTREE, filterstr=search_user,
                         attrlist=ldap_attributes)
    final_results = []
    for result in results:
        _, result_data = result
        if "sAMAccountName" not in result_data:
            # users without login probably aren't people
            continue
        final_results.append({
            attr: result_data[ldap_attr][0].decode("utf8")
            for attr, ldap_attr in zip(attributes, ldap_attributes)
            if result_data.get(ldap_attr)
        })
        if len(final_results) == max_results:
            break
    # l.unbind_s()  # disconnect
    return final_results


class GroupDoesNotExist(Exception):
    pass


users_parser = reqparse.RequestParser()
users_parser.add_argument("search", type=str, default="")
users_parser.add_argument("groups", type=str, default="")


class UsersResource(Resource):

    """
    Note: The list of users is just taken from the underlying
    system. Elogy does not really know or care where users come from,
    it just stores the authors as arbitrary strings. This is intended
    as a convenient way look up user names, not for authentication.

    search: arbitrary string that will be matched against logins and
            full names.
    groups: a list of group names to restrict the search to
            (currently has no effect if using LDAP
    """

    @marshal_with(fields.user, envelope="users")
    def get(self):

        args = users_parser.parse_args()
        search = args.get("search")
        if not search:
            return []

        # if LDAP is configured, let's check that
        LDAP_SERVER = current_app.config.get("LDAP_SERVER")
        LDAP_BASEDN = current_app.config.get("LDAP_BASEDN")

        if LDAP_SERVER and LDAP_BASEDN and len(search) > 1:
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
