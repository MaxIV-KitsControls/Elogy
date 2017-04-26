/* A single, full entry */

import React from 'react';
import {findDOMNode} from 'react-dom';
import {Link} from 'react-router-dom';

import style from './entry.css';
import {formatTimeString} from './util.js';


const EntryAttributes = ({attributes, logbook}) => (
    <div className="attributes">
        {
            logbook.attributes
                   .filter(attr => attributes[attr.name])
                   .map((attr, i) => <span key={i} className="attribute">{attr.name}: <span className="value">{attributes[attr.name]}</span></span>)
        }
    </div>
);


const ICON_CLASS_MAP = {
    "application/vnd.ms-excel": "fa fa-file-excel-o",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "fa fa-file-excel-o",
    'application/pdf': "fa fa fa-file-pdf-o",
    "text/plain": "fa fa-file-text",
    "text/csv": "fa fa-file-text",
    'application/zip': "fa fa-file-archive-o"
    // TODO: detect more file types
}


export const AttachmentPreview = ({attachment}) => {
    // display an appropriate icon for the given attachment
    if (!attachment.content_type)
        return <i className="fa fa-file-o fa-2x"/>
    const contentType = attachment.content_type.split(";")[0].toLowerCase();
    console.log("attachment", attachment, contentType);
    if (ICON_CLASS_MAP[contentType]) {
        return <i className={ICON_CLASS_MAP[attachment.content_type] + " fa-2x"}/>;
    }
    if (attachment.metadata && attachment.metadata.thumbnail_size)
        return <img src={`/attachments/${attachment.path}.thumbnail`}
                    width={attachment.metadata.thumbnail_size.width}
                    height={attachment.metadata.thumbnail_size.height}/>
    return <i className="fa fa-file-o fa-2x"/>;
};


export const EntryAttachments = ({attachments}) => (
    <div className="attachments">
        {
            attachments
                .map((att, i) => (
                    <span className="attachment" key={i} title={att.filename}>
                        <a href={`/attachments/${att.path}`}>
                            <AttachmentPreview attachment={att}/>
                        </a>
                    </span>
                ))
        }
    </div>
)


// An "entry" may have "followup" entries attached, and so on, so in
// practice we may display a whole tree of related entries here.
class InnerEntry extends React.Component {

    componentDidUpdate() {
        findDOMNode(this).scrollIntoView();
    }
    
    render () {

        const followups = this.props.followups ?
                          this.props.followups.map(
                              (followup, i) => <InnerEntry key={followup.id}
                                                           className="followupd"
                                                           followupNumber={i}
                                                           logbook={this.props.logbook}
                                                           {...followup}/>)
                        : null;

        const nonEmbeddedAttachments = this.props.attachments.filter(a => !a.embedded);
        const attachments = nonEmbeddedAttachments.length > 0?
                            <EntryAttachments attachments={nonEmbeddedAttachments}/>
                          : null;
        
        return (
            <div>
                <article>
                    <div className="info">
                        
                        <div className="commands">
                            <Link to={`/logbooks/${this.props.logbook.id}/entries/${this.props.id}`}>
                                Link
                            </Link>
            &nbsp;|&nbsp;
            <Link to={`/logbooks/${this.props.logbook.id}/entries/${this.props.id}/new`}>
                Followup
            </Link>
            &nbsp;|&nbsp;
            <Link to={`/logbooks/${this.props.logbook.id}/entries/${this.props.id}/edit`}>
                Edit
            </Link>
                        </div>
                        
                        <div>
                            
                            {
                                this.props.followupNumber !== undefined ?
                                <span className="followup-number">
                                    {this.props.followupNumber + 1}
                                </span>
                                : null
                            }

                <span className="created-at">
                    {formatTimeString(this.props.created_at)}
                </span>
                
                {
                    this.props.last_changed_at?
                    <span className="last-changed-at">
                        (Last change: {formatTimeString(this.props.last_changed_at)})
                    </span>
                    :null
                }
                
                        </div>
                        
                        <div className="authors">
                            {this.props.authors.map(
                                 (author, i) => <span key={i} className="author">{author}</span>)}
                        </div>
                        
                        {
                            this.props.logbook?
                            <EntryAttributes {...this.props}/>
                            : null
                        }
                    </div>
                    {
                        this.props.content_type.slice(0, 9) === "text/html"?
                        <div className="content"
                             dangerouslySetInnerHTML={
                                 {__html: this.props.content}
                                                     }/>
                        : <div className="content">{this.props.content}</div>
                    }
            
                    {attachments}
                </article>
                <div className="followups">{ followups }</div>
            </div>
        );
    }
}


class Entry extends React.Component {

    constructor () {
        super();
        this.state = {
            id: null,
            logbook: null,
            title: "",
            authors: [],
            content: ""
        };
    }

    fetchEntry (logbookId, entryId) {
        fetch(`/api/entries/${entryId}`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState(json));        
    }
    
    componentWillMount () {
        this.fetchEntry(this.props.match.params.logbookId,
                        this.props.match.params.entryId);
    }
    
    componentWillReceiveProps (newProps) {
        console.log("state", this.state);
        if (newProps.match.params.entryId != this.state.id
            || (this.state.logbook && (newProps.match.params.logbookId !== this.state.logbook.id))) {
            this.fetchEntry(newProps.match.params.logbookId,
                            newProps.match.params.entryId);
        }
    }
    
    render () {

        console.log("render", this.state);

        if (!(this.state.id && this.state.logbook)) {
            return <div>No entry selected!</div>
        }
            
        return (
            <div className="container">
                {/* The header will always stay at the top */}
                <header>
                    {this.state.logbook?
                     <span className="commands">
                         
                         {
                             this.state.follows?
                             <Link to={`/logbooks/${this.state.logbook.id}/entries/${this.state.follows}`}>Parent</Link>
                             : null
                         }
                         
                         <Link to={`/logbooks/${this.state.logbook.id}/entries/${this.state.previous}`}>Prev</Link>
                     &nbsp;|&nbsp;
                     <Link to={`/logbooks/${this.state.logbook.id}/entries/${this.state.next}`}>Next</Link>
                     </span>                     
                     : null}

                <Link to={`/logbooks/${this.state.logbook.id}/entries/${this.state.id}`}>
                    <span className="logbook">
                        <i className="fa fa-book"/> 
                        {this.state.logbook && this.state.logbook.name}
                    </span>
                </Link>
                
                <span className="title">
                    <i className="fa fa-file-text-o"/> 
                    {this.state.title}
                </span>
                </header>
                {/* The body is scrollable */}
                <div className="body">
                    <InnerEntry {...this.state}/>
                </div>
            </div>
        );
    }      
}


export default Entry;
