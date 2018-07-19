import React from "react";
import { Route } from "react-router-dom";
import { parseQuery } from "./util.js";
import "./search.css";

class QuickSearch extends React.Component {
    constructor() {
        super();
        this.state = {
            content: null,
            title: null,
            authors: null,
            attachments: null,
            ignore_children: false
        };
    }

    onChange(event) {
        this.setState({ [event.target.name]: event.target.value });
    }

    onToggleChildLogbooks(event) {
        this.setState({ ignore_children: !this.state.ignore_children });
    }

    onSubmit(history, event) {
        event.preventDefault(); // skip the normal server form submit

        // Some wrangling of query parameters to get a proper search
        // string that we can attach to the location. The point is that
        // keeping all the important state in the URL is good for bookmarking
        // and sharing.
        const query = Object.keys(this.state)
            .filter(key => this.state[key])
            .map(key => `${key}=${this.state[key]}`);

        // The parent parameter also needs to be kept around because it
        // is used to limit the set of visible logbooks.
        const parent = parseQuery(this.props.location.search)["parent"];
        if (parent) {
            query.push(`parent=${parent}`);
        }
        history.push({
            pathname: `/logbooks/${this.props.match.params.logbookId || 0}`,
            search: `?${query.join("&")}`,
            state: this.state
        });
    }

    onReset(history, event) {
        this.setState(
            {
                content: null,
                title: null,
                authors: null,
                attachments: null,
                ignore_children: false
            },
            this.onSubmit.bind(this, history, event)
        );
    }

    render() {
        return (
            // This is a slightly ugly way of injecting the browser history
            // into the component so that we can navigate programmatically
            // when the form is submitted...
            <Route
                render={({ history }) => (
                    <form
                        id="search"
                        onSubmit={this.onSubmit.bind(this, history)}
                        className={this.props.match.params.logbookId ? "logbook-selected" : "logbook-not-selected"}
                    >
                        <span title="Filters which can be used to limit the entries that are displayed.">
                            Search
                        </span>
                        <input
                            style={{ width: "100%" }}
                            name="title"
                            value={this.state.title || ""}
                            title="Filter entries on title (supports regular expressions)"
                            type="text"
                            ref="title"
                            placeholder="Title"
                            onChange={this.onChange.bind(this)}
                        />
                        <input
                            style={{ width: "100%" }}
                            name="content"
                            value={this.state.content || ""}
                            title="Filter entries on contents (supports regular expressions)"
                            type="text"
                            ref="content"
                            placeholder="Content"
                            onChange={this.onChange.bind(this)}
                        />
                        <input
                            style={{ width: "100%" }}
                            name="authors"
                            value={this.state.authors || ""}
                            title="Filter entries on authors (supports regular expressions)"
                            type="text"
                            ref="authors"
                            placeholder="Authors"
                            onChange={this.onChange.bind(this)}
                        />
                        <input
                            style={{ width: "100%" }}
                            name="attachments"
                            value={this.state.attachments || ""}
                            title="Filter entries on attachments (supports regular expressions)"
                            type="text"
                            ref="attachments"
                            placeholder="Attachments"
                            onChange={this.onChange.bind(this)}
                        />
                        <label title="Whether to include entries in logbooks contained in the selected logbook.">
                            <input
                                type="checkbox"
                                checked={!this.state.ignore_children}
                                onChange={this.onToggleChildLogbooks.bind(this)}
                            />
                            Recursive
                        </label>
                        <fieldset>
                            <input type="submit" value="Search" />
                            <input
                                type="button"
                                value="Clear"
                                onClick={this.onReset.bind(this, history)}
                            />
                        </fieldset>
                    </form>
                )}
            />
        );
    }
}

export default QuickSearch;
