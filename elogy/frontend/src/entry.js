/* A single, full entry */

import React from 'react';
import {findDOMNode} from 'react-dom';
import {Link} from 'react-router-dom';

import style from './entry.css';
import {formatDateTimeString} from './util.js';
import EntryAttributes from "./entryattributes.js";
import EntryAttachments from "./entryattachments.js";


// An "entry" may have "followup" entries attached, and so on, so in
// practice we may display a whole tree of related entries here.
export class InnerEntry extends React.Component {

    componentDidMount() {
        if (this.props.currentEntryId == this.props.id) 
            this.props.scrollToEntry(findDOMNode(this.refs.entry));
    }
    
    render () {

        const logbook = this.props.logbook;
        const followups = this.props.followups ?
                          this.props.followups.map(
                              (followup, i) => <InnerEntry
                                                   key={followup.id}
                                                   className="followupd"
                                                   followupNumber={i}
                                                   logbook={this.props.logbook}
                                                   scrollToEntry={this.props.scrollToEntry}
                                                   currentEntryId={this.props.currentEntryId}
                                                   {...followup}/>) :
                          null;

        const nonEmbeddedAttachments = this.props.attachments.filter(a => !a.embedded);
        const attachments = nonEmbeddedAttachments.length > 0?
                            <EntryAttachments attachments={nonEmbeddedAttachments}/>
                          : null;
        const followupNumber = this.props.followupNumber !== undefined ?
                               <span className="followup-number">
                                   <span className="fa fa-reply"/>
                                   &nbsp;                                   
                                   {this.props.followupNumber + 1}
                                   &nbsp;&nbsp;
                               </span> :
                               null;
        const lastChangedAt = this.props.last_changed_at?
                              <span className="last-changed-at">
                                  &nbsp;&nbsp;
                                  <i className="fa fa-pencil"/>&nbsp;
                                  {formatDateTimeString(this.props.last_changed_at)}
                              </span>
                             :null;
        const authors = this.props.authors.map((author, i) =>
            <span key={i} className="author">
                { author.name }
            </span>);

        const attributes = this.props.logbook?
                           <EntryAttributes {...this.props}/> :
                           null;

        const content = (
            this.props.content_type.slice(0, 9) === "text/html"?
            <div className="content" ref="entry"
                 dangerouslySetInnerHTML={{__html: this.props.content}}/> :
            <div className="content">{this.props.content}</div>
        );

        return (
            <div>
                <article>
                    <div className={"info" + (this.props.currentEntryId === this.props.id?
                                    " current" : "")}>

                        <div className="commands">
                            <Link to={`/logbooks/${logbook.id}/entries/${this.props.id}`}>
                                Link
                            </Link>
                            &nbsp;|&nbsp;
                            <Link to={`/logbooks/${logbook.id}/entries/${this.props.id}/edit`}>
                                Edit
                            </Link>
                        </div>
                        <div>
                            { followupNumber }
                            <span className="created-at">
                                <i className="fa fa-clock-o"/> {formatDateTimeString(this.props.created_at)}
                            </span>
                            { lastChangedAt }
                        </div>
                        <div className="authors">
                            <i className="fa fa-user"/> { authors }
                        </div>
                        { attributes }
                    </div>
                    { content }
                    { attachments }
                </article>
                
                <div className="followups">
                    { followups }
                </div>
            </div>
        );
    }
}


class Entry extends React.Component {

    constructor () {
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

    fetchEntry (logbookId, entryId) {
        /*         this.setState({loading: true});*/
        fetch(`/api/logbooks/${logbookId}/entries/${entryId}/`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState({loading: false, ...json}));        
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

    scrollToEntry (element) {
        setTimeout(() => element.scrollIntoView(), 100);
    }
    
    render () {

        if (!(this.state.id && this.state.logbook)) {
            return <div>No entry selected!</div>
        }

        const logbook = this.state.logbook;
        
        return (
            <div className="container">
                
                {/* The header will always stay at the top */}
                <header>
                    {
                        this.state.logbook?
                        <span className="commands">

                            {
                                this.state.follows?
                                <Link to={`/logbooks/${logbook.id}/entries/${this.state.follows}`}>Parent</Link>
                                : null
                            }
                            
                            <Link to={`/logbooks/${logbook.id}/entries/${this.state.previous}`}>Prev</Link>
                        &nbsp;|&nbsp;
                        <Link to={`/logbooks/${logbook.id}/entries/${this.state.next}`}>Next</Link>
                        &nbsp;&nbsp;

                        <Link to={`/logbooks/${logbook.id}/entries/${this.state.id}/new`}>
                            Followup
                        </Link>                        
                        &nbsp;|&nbsp;
                        <Link to={`/logbooks/${logbook.id}/entries/new`}>New Entry</Link>
                        
                        </span>    
                        : null
                    }
                    
                    <Link to={`/logbooks/${logbook.id}/entries/${this.state.id}`}>
                        <span className="logbook">
                            <i className="fa fa-book"/> {this.state.logbook && this.state.logbook.name}
                        </span>
                    </Link>
                    
                    <div className="title">
                        {this.state.title}
                    </div>
                </header>
                
                {/* The body is scrollable */}
                <div className="body">
                    <div ref="body">
                        <InnerEntry {...this.state}
                                    scrollToEntry={this.scrollToEntry.bind(this)}
                                    currentEntryId={parseInt(this.props.match.params.entryId)}/>
                        
                    </div>
                </div>
            </div>
        );
    }      
}


export default Entry;
