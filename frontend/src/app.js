/* The main file that ties together the various components into an "app" */

import React from "react";
import { BrowserRouter as Router, Route, Switch } from "react-router-dom";
import { Link } from "react-router-dom";

import Entry from "./entry.js";
import EntryEditor from "./entryeditor.js";
import Logbook from "./logbook.js";
import LogbookEditor from "./logbookeditor.js";
import LogbookTree from "./logbooktree.js";
import QuickSearch from "./search.js";
import EventBus from "./eventsystem.js";
import { withProps } from "./util.js";
import "./app.css";

// A common eventbus that allows simple communication between
// components. Should only be used for simple things like
// asking a component to reload. If we start using it for passing
// data around we'd better switch to Redux or something.
const eventbus = new EventBus();

// wrap the relevant component with the eventbus as a prop
// This is the only (?) way to send props to a route component
const LogbookTreeWithEventbus = withProps(LogbookTree, { eventbus });
const LogbookWithEventbus = withProps(Logbook, { eventbus });
const EntryEditorWithEventbus = withProps(EntryEditor, { eventbus });
const LogbookEditorWithEventbus = withProps(LogbookEditor, { eventbus });

// dummy components for when no logbook is selected
class NoLogbook extends React.Component {
    render() {
        return (
            <div className="empty">
                <i className="fa fa-arrow-left" /> Select a logbook
                <div>
                    {" "}
                    or{" "}
                    <Link
                        to={{
                            pathname: "/logbooks/0/new",
                            search: window.location.search
                        }}
                    >
                        create a new one
                    </Link>.
                </div>
            </div>
        );
    }
}

class NoEntry extends React.Component {
    // a dummy for when no entry is selected

    render() {
        const logbookId = parseInt(this.props.match.params.logbookId);
        return (
            <div className="empty">
                <i className="fa fa-arrow-left" /> Select an entry to read it
                {logbookId ? (
                    <div>
                        {" "}
                        or{" "}
                        <Link
                            to={{
                                pathname: `/logbooks/${logbookId}/entries/new`,
                                search: window.location.search
                            }}
                        >
                            click here to make a new entry.
                        </Link>
                    </div>
                ) : null}
            </div>
        );
    }
}

const Elogy = () => (
    /* Set up a browser router that will render the correct component
       in the right places, all depending on the current URL.  */

    <Router>
        <div id="app">
            <div id="logbooks">
                <Switch>
                    <Route
                        path="/logbooks/:logbookId"
                        component={LogbookTreeWithEventbus}
                    />
                    <Route component={LogbookTreeWithEventbus} />
                </Switch>
                <Switch>
                    <Route
                        path="/logbooks/:logbookId"
                        component={QuickSearch}
                    />
                    <Route component={QuickSearch} />
                </Switch>
            </div>

            <div id="logbook">
                <Switch>
                    <Route
                        path="/logbooks/:logbookId/entries/:entryId"
                        component={LogbookWithEventbus}
                    />
                    <Route
                        path="/logbooks/:logbookId"
                        component={LogbookWithEventbus}
                    />
                    <Route component={NoLogbook} />
                </Switch>
            </div>

            <div id="entry">
                <Switch>
                    <Route
                        path="/logbooks/:logbookId/entries/new"
                        component={EntryEditorWithEventbus}
                    />
                    <Route
                        path="/logbooks/:logbookId/entries/:entryId/:command"
                        component={EntryEditorWithEventbus}
                    />

                    <Route
                        path="/logbooks/:logbookId/entries/:entryId"
                        component={Entry}
                    />

                    <Route
                        path="/logbooks/new"
                        component={LogbookEditorWithEventbus}
                    />
                    <Route
                        path="/logbooks/:logbookId/:command"
                        component={LogbookEditorWithEventbus}
                    />

                    <Route path="/logbooks/:logbookId" component={NoEntry} />
                </Switch>
            </div>
        </div>
    </Router>
);

export default Elogy;
