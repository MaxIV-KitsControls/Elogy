import React from 'react';
import {findDOMNode} from 'react-dom';
import {Link} from 'react-router-dom';
import update from 'immutability-helper';

import {parseQuery, groupBy} from "./util.js";
import style from './logbook.css';
import {AttachmentPreview} from "./entry.js";


const EntryPreview = ({logbook, entry, selected, search}) => (
    <div key={entry.id} className="entry">
        <Link to={`/logbooks/${logbook && logbook.id || 0}/entries/${entry.id}${search || ""}`}>
            
            {
                entry.n_attachments?
                <div className="attachments">
                    {entry.attachment_preview?
                     <AttachmentPreview attachment={entry.attachment_preview}/>
                     :null
                    }
                {/* width={entry.attachments[0].thumbnail_size.width}
                    height={entry.attachments[0].thumbnail_size.height}/> */}
                    <span>{ entry.n_attachments }</span>
                </div>
                : null
            }
            {
                logbook && (logbook.id !== entry.logbook.id)?
                <div className="logbook">{entry.logbook.name}</div>
                : null
            }
        <div className="info">
            <span className="timestamp">
                { (new Date(Date.parse(entry.last_changed_at || entry.created_at))).toLocaleTimeString() }
            </span>
            <span className="authors">
                { entry.authors.slice(0, 2).map(
                      (author, i) => <span key={i} className="author">{author}</span>) }
                { entry.authors.length > 2? `, (+${entry.authors.length-2})` : null }
            </span>            
        </div>

            <div className="title"><span>{ entry.title }</span></div>
            <div className="content"> {entry.content}</div>

            {
                entry.n_followups > 0?
                <div className="followups">{ entry.n_followups }</div>
                : null
            }
        </Link>
    </div>
)


class EntryPreviews extends React.Component {
    
    constructor () {
        super();
        this.state = {
            entries: []            
        }
    }

    /* componentDidUpdate (oldProps) {
     *     if (oldProps.selectedEntryId !== this.props.selectedEntryId)
     *         this.refs[this.props.selectedEntryId].scrollIntoView();
     * }*/
    
    render () {

        /* First, we'll group the entries according to date of creation */
        const dateGroups = groupBy(
            this.props.entries,
            entry => (new Date(
                Date.parse(entry.last_changed_at || entry.created_at))
                .toDateString())
        );

        /* Now we'll build a nested DOM structure where each date contains 
           the entries for that date. */
        const entries = Object
            .keys(dateGroups)
            .map(date => (
                <dl key={date} className="date-group">
                    <dt className="date">{date}</dt>
                    {dateGroups[date]
                        .map((entry, i) => (
                            <dd key={i}
                                className={"entry" + (this.props.selectedEntryId == entry.id? " selected" : "")}
                                ref={entry.id}>
                                <EntryPreview
                                    key={entry.id}
                                    search={this.props.search}
                                    logbook={this.props.logbook} entry={entry}/>
                            </dd>
                        ))
                    }
                </dl>
            ));

        return (
            <div ref="container" className="entries">
                {entries}
            </div>
        );
    }
}


class Logbook extends React.Component {

    constructor () {
        super();
        this.state = {
            logbook: {},
            entries: [],
            attributeFilters: {}
        }
    }

    // Fetch all information (but only the first few entries)
    fetch (logbookId, search, attributeFilters, offset, n) {
        const query = search? parseQuery(search) : {};
        query.attributes = Object.keys(attributeFilters)
                                 .filter(key => attributeFilters[key])
                                 .map(key => `${key}:${attributeFilters[key]}`)
                                 .join(",");
        query["n"] = n || query["n"] || 50;
        query["offset"] = offset || query["offset"] || 0;
        const newSearch = Object.keys(query)
                                .map(key => `${key}=${query[key]}`)
                                .join("&");
        fetch(`/api/logbooks/${logbookId || 0}/entries/?${newSearch || ""}`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState(json));
    }

    // fill with more entries
    // TODO: lots of repetition here...
    fetchMoreEntries (n) {
        const query = this.props.location.search? parseQuery(this.props.location.search) : {};
        query.attributes = Object.keys(this.state.attributeFilters)
                                 .filter(key => this.state.attributeFilters[key])
                                 .map(key => `${key}:${this.state.attributeFilters[key]}`)
                                 .join(",");
        query["n"] = n || query["n"] || 50;
        query["offset"] = this.state.entries.length;
        const newSearch = Object.keys(query)
                                .map(key => `${key}=${query[key]}`)
                                .join("&");
        fetch(`/api/logbooks/${this.props.match.params.logbookId || 0}/entries/?${newSearch || ""}`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState(update(this.state, {entries: {$push: json.entries}})));
    }
    
    componentWillMount () {
        this.fetch(this.props.match.params.logbookId,
                   this.props.location.search,
                   this.state.attributeFilters);
    }
    
    componentWillUpdate (newProps, newState) {
        if ((newProps.match.params.logbookId !==
            this.props.match.params.logbookId ||
             newProps.location.search !== this.props.location.search) ||
            (newState.attributeFilters !== this.state.attributeFilters) ||
            (newProps.location.state && newProps.location.state.reloadLogbook)) {
            this.fetch(newProps.match.params.logbookId,
                       newProps.location.search,
                       newState.attributeFilters);
        }
        if (newProps.match.params.logbookId !==
            this.props.match.params.logbookId) {
            this.setState(update(this.state, {attributeFilters: {$set: {}}}));
        }
             
    }

    /* shouldComponentUpdate (newProps, newState) {
     *     return ((newProps.match.params.logbookId !==
     *         this.props.match.params.logbookId ||
     *              newProps.location.search !== this.props.location.search) ||
     *             newState.attributeFilters !== this.state.attributeFilters)
     * }*/

    componentDidUpdate() {
        console.log("title", this.state.logbook);
        document.title = `${this.state.logbook.name}`
    }
    
    onChangeAttributeFilter (attribute, event) {
        if (event.target.selectedIndex == 0) {
            this.setState(update(
                this.state, {
                    attributeFilters: {[attribute]: {$set: undefined}}
                }
            ));
        } else {
            const value = event.target.value;            
            this.setState(update(
                this.state, {
                    attributeFilters: {[attribute]: {$set: value}}
                }
            ));
        }
    }

    onLoadMore () {
        this.fetchMoreEntries();
    }

    componentDidUpdate() {
        findDOMNode(this.refs.entries).scrollIntoView();
    }    
    
    render() {

        const logbook = this.state.logbook,
              entryId = this.props.match.params.entryId?
                        parseInt(this.props.match.params.entryId)
                      : null,
              query = parseQuery(this.props.location.search),
              filter = ["title", "content", "authors"]
                  .filter(key => query[key])
                  .map(key => (
                      <span key={key} className="filter">
                          {key}: "{query[key]}"
                      </span>)),
              attributes = this.state.logbook.attributes?
                           this.state.logbook.attributes
                               .filter(attr => attr.type == "option" || attr.type == "multioption")
                               .map(
                                   attr => (
                                       <select key={attr.name} onChange={this.onChangeAttributeFilter.bind(this, attr.name)}>
                                           <option>[{attr.name}]</option>
                                           {attr.options.map((o, i) => <option key={i}>{o}</option>)}
                                       </select>
                                   ))
                         : null;
        
        return (
            <div>
                <header>
                    { logbook.id && logbook.name }
                    { logbook.id &&
                      <div>
                          <Link to={`/logbooks/${this.state.logbook.id}?parent=${this.state.logbook.id}`}>
                              Make parent
                          </Link>
                          <Link to={`/logbooks/${this.state.logbook.id}/entries/new`}>New entry</Link>
                      </div>
                      
                    }
                    <Link to={`/logbooks/${this.state.logbook.id}/edit`}>Edit</Link>
                    <div className="filters"> {filter} </div>
                    <div className="attributes">
                        {attributes}
                    </div>
                </header>
                <div ref="entries">
                    <EntryPreviews logbook={logbook}
                                   entries={this.state.entries}
                                   search={this.props.location.search}
                                   selectedEntryId={entryId}/>
                    <div onClick={this.onLoadMore.bind(this)}>
                        Load more (showing {this.state.entries.length} of {this.state.count})
                    </div>
                </div>
            </div>
        );
    }
}


export default Logbook;
