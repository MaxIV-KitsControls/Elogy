import pwd
import grp

from flask import jsonify
from flask_restful import Resource, marshal_with, reqparse


users_parser = reqparse.RequestParser()
users_parser.add_argument("search", type=str, default="")
users_parser.add_argument("groups", type=str, default="")


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

    def get(self):
        args = users_parser.parse_args()
        search = args.get("search", "")
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
        return jsonify(users=candidates)
