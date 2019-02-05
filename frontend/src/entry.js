/* Display a full entry together with any followups */

import React from "react";
import { findDOMNode } from "react-dom";
import { Link } from "react-router-dom";
import Mark from "mark.js";
import { withRouter } from 'react-router-dom';

import "./entry.css";
import { formatDateTimeString } from "./util.js";
import { parseQuery } from "./util.js";
import EntryAttributes from "./entryattributes.js";
import EntryAttachments from "./entryattachments.js";

// This component renders an entry.
// An "entry" may have "followup" entries attached, and so on, so in
// practice we may display a whole tree of related entries here.
export class InnerEntry extends React.Component {
    componentDidMount() {
        this.highlightContentFilter();
        this.scrollToCurrentEntry();
    }

    componentDidUpdate() {
        this.highlightContentFilter();
        this.scrollToCurrentEntry();
    }

    scrollToCurrentEntry() {
        if (this.props.currentEntryId === this.props.id) {
            var node = findDOMNode(this.refs.article);
            setTimeout(node.scrollIntoView(true));
        }
    }

    highlightContentFilter() {
        // highlight the current content filter string in the content
        if (this.props.contentFilter) {
            const mark = new Mark(findDOMNode(this.refs.content));
            mark.markRegExp(new RegExp(this.props.contentFilter, "gmi"));
        }
    }

    render() {
        const logbook = this.props.logbook;
        const followups = this.props.followups
            ? this.props.followups.map((followup, i) => (
                  <InnerEntry
                      key={followup.id}
                      className="followupd"
                      followupNumber={i}
                      logbook={this.props.logbook}
                      currentEntryId={this.props.currentEntryId}
                      contentFilter={this.props.contentFilter}
                      {...followup}
                  />
              ))
            : null;

        const nonEmbeddedAttachments = this.props.attachments.filter(
            a => !a.embedded
        );
        const attachments =
            nonEmbeddedAttachments.length > 0 ? (
                <EntryAttachments attachments={nonEmbeddedAttachments} />
            ) : null;
        const followupNumber =
            this.props.followupNumber !== undefined ? (
                <span className="followup" title="This is a follow-up">
                    <span className="fa fa-comment" />
                    &nbsp;&nbsp;
                </span>
            ) : null;
        const lastChangedAt = this.props.last_changed_at ? (
            <span
                className="timestamp last-changed-at"
                title="The entry was last edited at this time"
            >
                &nbsp;&nbsp;
                <i className="fa fa-pencil" />&nbsp;
                {formatDateTimeString(this.props.last_changed_at)}
            </span>
        ) : null;
        const lock = this.props.lock ? (
            <span
                title={`The entry is locked for editing by ${this.props.lock
                    .owned_by_ip} since ${this.props.lock.created_at}`}
                className="lock fa fa-lock"
            />
        ) : null;

        const authors = this.props.authors.map((author, i) => (
            <span
                key={i}
                className="author"
                title={`${author.email || "No email"} (${author.login ||
                    "No login"})`}
            >
                {author.name}
            </span>
        ));

        const attributes = this.props.logbook ? (
            <EntryAttributes {...this.props} />
        ) : null;

        const content =
            this.props.content_type.slice(0, 9) === "text/html" ? (
                <div
                    className="content html"
                    ref="content"
                    dangerouslySetInnerHTML={{ __html: this.props.content }}
                />
            ) : (
                <div className="content plain">{this.props.content}</div>
            );

        const link = !this.props.hideLink ? (
            <Link
                to={`/logbooks/${logbook.id}/entries/${this.props.id}`}
                title="A direct link to this entry"
            >
                Link
            </Link>
        ) : null;

        const editLink = !this.props.hideEditLink ? (
            <Link
                to={{
                    pathname: `/logbooks/${logbook.id}/entries/${this.props
                        .id}/edit`,
                    search: window.location.search
                }}
                title="Make changes to this entry"
            >
                {lock} Edit
            </Link>
        ) : null;
        return (
            <div>
                <article ref="article">
                    <div
                        className={
                            "info" +
                            (this.props.currentEntryId === this.props.id
                                ? " current"
                                : "")
                        }
                    >
                        <div className="commands">
                            {link} {editLink}
                        </div>
                        <div>
                            {followupNumber}
                            <span
                                className="timestamp created-at"
                                title="The entry was created at this time"
                            >
                                {" "}
                                {formatDateTimeString(this.props.created_at)}
                            </span>
                            {lastChangedAt}
                        </div>
                        <div className="authors">
                            <span className="fa fa-user" /> {authors}
                        </div>
                        {attributes}
                    </div>
                    {content}
                    {attachments}
                </article>

                <div className="followups">{followups}</div>
            </div>
        );
    }
}

// entry display including a header
class Entry extends React.Component {
    constructor() {
        super();
        this.state = {
            loading: false,
            id: null,
            logbook: null,
            title: "",
            authors: [],
            content: ""
        };
    }

    fetchEntry(logbookId, entryId) {
        fetch(`/api/logbooks/${logbookId}/entries/${entryId}/?thread=true`, {
            headers: { Accept: "application/json" }
        })
            .then(response => response.json())
            .then(json => this.setState({ loading: false, ...json.entry }));
    }

    componentWillMount() {
        this.fetchEntry(
            this.props.match.params.logbookId,
            this.props.match.params.entryId
        );
    }

    componentWillReceiveProps(newProps) {
        if (
            newProps.match.params.entryId !== this.state.id ||
            (this.state.logbook &&
                newProps.match.params.logbookId !== this.state.logbook.id)
        ) {
            this.fetchEntry(
                newProps.match.params.logbookId,
                newProps.match.params.entryId
            );
        }
    }

    render() {
        if (!(this.state.id && this.state.logbook)) {
            return <div />; // placeholder
        }

        const logbook = this.state.logbook;
        const nextLink = this.state.next ? (
            <Link
                to={`/logbooks/${logbook.id}/entries/${this.state.next}`}
                title="Go to the next chronological entry in this logbook"
            >
                Next
            </Link>
        ) : (
            "Next"
        );
        const prevLink = this.state.previous ? (
            <Link
                to={`/logbooks/${logbook.id}/entries/${this.state.previous}`}
                title="Go to the previous chronological entry in this logbook"
            >
                Prev
            </Link>
        ) : (
            "Prev"
        );

        const query = parseQuery(this.props.location.search);
        return (
            <div className="container" ref="container">
            <button className="mobile-back-button" onClick={() => this.props.history.push('/logbooks/' + logbook.id)}> Back </button>
                {/* The header will always stay at the top */}
                <header>
                    {this.state.logbook ? (
                        <span className="commands">
                            {this.state.follows ? (
                                <Link
                                    to={{
                                        pathname: `/logbooks/${logbook.id}/entries/${this
                                            .state.follows}`,
                                        search: window.location.search
                                    }}
                                    title="Go to the entry this one is a followup to"
                                >
                                    Parent
                                </Link>
                            ) : null}
                            <Link
                                to={{
                                    pathname: `/logbooks/${logbook.id}/entries/${this
                                        .state.id}/new`,
                                    search: window.location.search
                                }}
                                title="Create a new entry that follows this one."
                            >
                                <i className="fa fa-comment" /> New Follow-up
                            </Link>
                            &nbsp;|&nbsp;
                            <Link
                                to={{
                                    pathname: `/logbooks/${logbook.id}/entries/new`,
                                    search: window.location.search
                                }}
                                title="Create a new entry in this logbook"
                            >
                                New Entry
                            </Link>
                        </span>
                    ) : null}

                    <Link
                        to={{
                            pathname: `/logbooks/${logbook.id}/entries/${this
                                .state.id}`,
                            search: window.location.search
                        }}
                    >
                        <span className="logbook">
                            <i className="fa fa-book" />{" "}
                            {this.state.logbook && this.state.logbook.name}
                        </span>
                    </Link>

                    <div className="title">{this.state.title}</div>
                </header>

                {/* The body is scrollable */}
                <div className="body">
                    <div ref="body">
                        <InnerEntry
                            {...this.state}
                            contentFilter={query.content}
                            currentEntryId={parseInt(
                                this.props.match.params.entryId,
                                10
                            )}
                        />
                    </div>
                </div>
            </div>
        );
    }
}

export default Entry;
