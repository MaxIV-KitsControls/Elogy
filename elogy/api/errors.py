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
    )
}
