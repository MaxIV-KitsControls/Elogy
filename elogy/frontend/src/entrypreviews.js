/* Display a list of entries in a compact way */

import React from 'react';
import {Link} from 'react-router-dom';
import LazyLoad from 'react-lazy-load';

import {AttachmentPreviewIcon} from "./entryattachments.js";
import {groupBy, formatTimeString, formatDateString} from "./util.js";


const EntryPreview = ({logbook, entry, selected, search=""}) => {
    
    const url = `/logbooks/${logbook.id}/entries/${entry.id}/${search}`
    const attachmentPreviewWidth = (entry.attachment_preview &&
                                    entry.attachment_preview.metadata.thumbnail_size &&
                                    entry.attachment_preview.metadata.thumbnail_size.width);
    const attachmentPreviewHeight = (entry.attachment_preview &&
                                     entry.attachment_preview.metadata.thumbnail_size &&
                                     entry.attachment_preview.metadata.thumbnail_size.height);

    const attachments = (
        entry.n_attachments ?
        <div className="attachments">
        {
            entry.attachment_preview?
            (<LazyLoad offsetVertical={500}
                       width={ attachmentPreviewWidth }
                       height={ attachmentPreviewHeight }>
                <AttachmentPreviewIcon attachment={entry.attachment_preview}/>
            </LazyLoad>) :
            null
        }
        {
            entry.n_attachments > 1?
            <span>{ entry.n_attachments }</span> :
            null
        }
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
    const timestamp = formatTimeString(entry.timestamp);
    const authors = entry.authors
                         .slice(0, 2)
                         .map((author, i) => <span key={i} className="author">{author}</span>);
    const allAuthors = entry.authors.join(",&nbsp;");
    // for space reasons, we only show up to the two frst authors
    // and then add a summary of the rest, e.g. "(+3)".
    const authorsEllipsis = entry.authors.length > 2?
                            `, (+${entry.authors.length-2})` :
                            null;
    const followups = entry.n_followups > 0?
                      <div className="followups"><span className="fa fa-reply"/>
                          { entry.n_followups }</div> :
                      null;
    const edited = entry.last_changed_at? <i className="fa fa-pencil"/> : null;
    
    return (
        <div key={entry.id} className="entry">
            <Link to={url}>
                { attachments }
                { followups }                                
                { logbookName }
                <div className="info">
                    <span className="timestamp">
                        <i className="fa fa-clock-o"/> { edited } { timestamp }
                    </span>
                    <span className="authors"
                          title={allAuthors}>
                        <i className="fa fa-user"/> { authors }{ authorsEllipsis }
                    </span>            
                </div>
                <div className="title"><span>{ entry.title }</span></div>
                <div className="content"> {entry.content}</div>
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
                            className={"entry" + (selectedEntryId === entry.id? " selected" : "")}>
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
            { entryPreviews.length > 0?
              entryPreviews :
              <div className="no-entries">
                  No matching entries!
              </div> }
        </div>
    );
}


export default EntryPreviews;
