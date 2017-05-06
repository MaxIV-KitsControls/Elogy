import React from 'react';
import {Link} from 'react-router-dom';

import {AttachmentPreview} from "./entryattachments.js";
import {groupBy, formatTimeString, formatDateString} from "./util.js";


const EntryPreview = ({logbook, entry, selected, search=""}) => {
    
    const url = `/logbooks/${logbook.id}/entries/${entry.id}${search}`
    const attachments = (
        entry.n_attachments ?
        <div className="attachments">
            {
                entry.attachment_preview?
                <AttachmentPreview
                    attachment={entry.attachment_preview}/> :
                null
            }
            <span>{ entry.n_attachments }</span>
        </div> :
        null
    );
    const logbookName = (
        logbook.id !== entry.logbook.id?
        <div className="logbook">
            <i className="fa fa-book"/> {entry.logbook.name}
        </div> :
        null
    );
    const timestamp = formatTimeString(entry.last_changed_at ||
                                       entry.created_at);
    const authors = entry.authors
                         .slice(0, 2)
                         .map((author, i) => <span key={i} className="author">{author}</span>);
    const authorsEllipsis = entry.authors.length > 2?
                            `, (+${entry.authors.length-2})` :
                            null;
    const followups = entry.n_followups > 0?
                      <div className="followups">{ entry.n_followups }</div> :
                      null;

    return (
        <div key={entry.id} className="entry">
            <Link to={url}>
                { attachments }
                { logbookName }
                <div className="info">
                    <span className="timestamp">
                        <i className="fa fa-clock-o"/> { timestamp }
                    </span>
                    <span className="authors">
                        <i className="fa fa-user"/> { authors }{ authorsEllipsis }
                    </span>            
                </div>
                <div className="title"><span>{ entry.title }</span></div>
                <div className="content"> {entry.content}</div>
                { followups }
            </Link>
        </div>
    );
}

const EntryPreviews = ({logbook, entries, selectedEntryId, search}) => {
    
    /* First, we'll group the entries according to date of creation */
    const dateGroups = groupBy(
        entries,
        entry => formatDateString(entry.last_changed_at || entry.created_at)
    );

    /* Now we'll build a nested DOM structure where each date contains 
       the entries for that date. */
    const entryPreviews = Object
        .keys(dateGroups)
        .map(date => (
            <dl key={date} className="date-group">
                <dt className="date">{date}</dt>
                {dateGroups[date]
                    .map((entry, i) => (
                        <dd key={i}
                            className={"entry" + (selectedEntryId == entry.id? " selected" : "")}>
                            <EntryPreview
                                key={entry.id}
                                search={search}
                                logbook={logbook}
                                entry={entry}/>
                        </dd>
                    ))
                }
            </dl>
        ));

    return (
        <div className="entries">
            { entryPreviews }
        </div>
    );
}


export default EntryPreviews;
