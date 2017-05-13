# Catch exceptions raised in API endpoints and translate them
# into useful error messages.
# Note: the Flask debugger will catch the exceptions before this.
errors = {
    "LogbookDoesNotExist": dict(
        message="Logbook does not exist!",
        status=404
    ),
    "EntryDoesNotExist": dict(
        message="Entry does not exist!",
        status=404
    ),
    "GroupDoesNotExist": dict(
        message="Group does not exist!",
        status=404
    ),
    "Locked": dict(
        message="Resource locked by someone else!",
        status=409
    ),
    "EntryLockDoesNotExist": dict(
        message="No lock on the entry!",
        status=404
    ),
    "EntryRevisionDoesNotExist": dict(
        message="Entry revision does not exist!",
        status=404
    )
}
