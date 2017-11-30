/* Display a list of entries in a compact way */

import React from "react";
import { Link } from "react-router-dom";
import LazyLoad from "react-lazy-load";

import { AttachmentPreviewIcon } from "./entryattachments.js";
import { groupBy, formatTimeString, formatDateString } from "./util.js";

const Tags = ({ attributes }) => {
    if (attributes && attributes.Tags) {
        const tags = attributes.Tags.map(tag => (
            <span key={tag} className="tag">
                {tag}
            </span>
        ));
        return <div className="tags">{tags}</div>;
    }
    return null;
};

const EntryPreview = ({ logbook, entry, selected, search = "" }) => {
    const url = `/logbooks/${logbook.id}/entries/${entry.id}/${search}`;
    const attachmentPreviewWidth =
        entry.attachment_preview &&
        entry.attachment_preview.metadata &&
        entry.attachment_preview.metadata.thumbnail_size &&
        entry.attachment_preview.metadata.thumbnail_size.width;
    const attachmentPreviewHeight =
        entry.attachment_preview &&
        entry.attachment_preview.metadata &&
        entry.attachment_preview.metadata.thumbnail_size &&
        entry.attachment_preview.metadata.thumbnail_size.height;

    const attachments = entry.n_attachments ? (
        <div className="attachments">
            {entry.attachment_preview ? (
                <LazyLoad
                    offsetVertical={500}
                    width={attachmentPreviewWidth}
                    height={attachmentPreviewHeight}
                >
                    <AttachmentPreviewIcon
                        attachment={entry.attachment_preview}
                    />
                </LazyLoad>
            ) : null}
            {entry.n_attachments > 1 ? (
                <span>{entry.n_attachments}</span>
            ) : null}
        </div>
    ) : null;
    const logbookName =
        logbook.id !== entry.logbook.id ? (
            <div className="logbook">
                <i className="fa fa-book" /> {entry.logbook.name}
            </div>
        ) : null;
    const timestamp = formatTimeString(entry.timestamp);
    const authors = entry.authors.slice(0, 2).map((author, i) => (
        <span key={i} className="author">
            {author}
        </span>
    ));
    const allAuthors = entry.authors.join(", ");
    // for space reasons, we only show up to the two frst authors
    // and then add a summary of the rest, e.g. "(+3)".
    const authorsEllipsis =
        entry.authors.length > 2 ? `, (+${entry.authors.length - 2})` : null;
    const followups =
        entry.n_followups > 0 ? (
            <div className="followups">
                <span className="fa fa-comment" />
                {entry.n_followups}
            </div>
        ) : null;
    const edited = entry.last_changed_at ? (
        <i className="fa fa-pencil" />
    ) : null;

    const editTime =
        entry.priority > 0 ? (
            <span className="timestamp">
                <i className="fa fa-thumb-tack" />
            </span>
        ) : (
            <span className="timestamp">
                <i className="fa fa-clock-o" /> {edited} {timestamp}
            </span>
        );

    return (
        <div key={entry.id} className={"entry"}>
            <Link to={url}>
                <div className="inner">
                    {attachments}
                    {logbookName}
                    <div className="info">
                        {editTime}
                        <span className="authors" title={allAuthors}>
                            <i className="fa fa-user" /> {authors}
                            {authorsEllipsis}
                        </span>
                    </div>
                    {followups}
                    <div className="title">
                        <span>{entry.title}</span>
                    </div>

                    <div className="content"> {entry.content}</div>
                </div>
                <Tags attributes={entry.attributes} />
            </Link>
        </div>
    );
};

const EntryPreviews = ({ logbook, entries, selectedEntryId, search }) => {
    /* First, we'll group the entries according to priority if set,
       otherwise date of creation */

    const dateGroups = groupBy(
        entries,
        /* 
           This is a bit hacky; the idea is that we want high priority posts
           grouped outside of the date groups, so we prepend the priority
           to the group key. There's probably a better way.
         */
        entry =>
            entry.priority !== 0
                ? -entry.priority
                : -entry.priority + "@" + formatDateString(entry.timestamp)
    );

    function getPriorityGroup(priority) {
        if (priority === 0) return;
        if (priority > 0 && priority <= 100) {
            return "pinned";
        }
        if (priority > 100 && priority <= 200) {
            return "important";
        }
    }

    /* Now we'll build a nested DOM structure where each group contains 
       the entries for that group. */
    /* Also note that we're relying on the object key ordering to be kept.
       This seems to be true, but AFAIK it's not really guaranteed... */
    const entryPreviews = Object.keys(dateGroups).map(priorityAndDate => {
        let [priority, date] = priorityAndDate.split("@");
        let priorityGroup = getPriorityGroup(-parseInt(priority));
        let group = priorityGroup || date;
        return (
            <dl key={priorityAndDate} className="date-group">
                <dt
                    className={"group" + (date ? " date" : " " + priorityGroup)}
                >
                    {group}
                </dt>
                {dateGroups[priorityAndDate].map((entry, i) => (
                    <dd
                        key={i}
                        className={
                            "entry " +
                            (selectedEntryId === entry.id ? " selected " : "") +
                            (priorityGroup || "") +
                            (entry.logbook.id == logbook.id ? " native" : "")
                        }
                    >
                        <EntryPreview
                            key={entry.id}
                            search={search}
                            logbook={logbook}
                            entry={entry}
                        />
                    </dd>
                ))}
            </dl>
        );
    });

    return (
        <div className="entries">
            {entryPreviews.length > 0 ? (
                entryPreviews
            ) : (
                <div className="no-entries">No matching entries!</div>
            )}
        </div>
    );
};

export default EntryPreviews;
