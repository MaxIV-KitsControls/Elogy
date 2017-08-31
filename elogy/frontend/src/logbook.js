/* Displays a logbook and the entries in it, after optional filtering */

import React from 'react';
import {findDOMNode} from 'react-dom';
import {Link} from 'react-router-dom';
import update from 'immutability-helper';

import {parseQuery} from "./util.js";
import EntryPreviews from "./entrypreviews.js";
import './logbook.css';


class Logbook extends React.Component {

    constructor () {
        super();
        this.state = {
            logbook: {},
            entries: [],
            attributeFilters: {},
            loading: false
        }
        this._reload = this.reload.bind(this)
    }

    // Fetch entries
    fetch (logbookId, search, attributeFilters, offset, n) {
        // build a nice query string with the query
        // we'll start with the parameters in the browser URL
        const query = search? parseQuery(search) : {};
        query["n"] = n || query["n"] || 50;
        query["offset"] = offset || 0;  // || query["offset"] || 0;
        const attributes = Object.keys(attributeFilters)
            .filter(key => attributeFilters[key])
            .map(key => `attribute=${key}:${attributeFilters[key]}`)
            .join("&");
        const newSearch = Object.keys(query)
                                .map(key => `${key}=${query[key]}`)
                                .join("&") + "&" + attributes;
        this.setState({loading: true});
        fetch(`/api/logbooks/${logbookId || 0}/entries/?${newSearch || ""}`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => {
                this.setState({loading: false});
                if (offset) {
                    // append the new entries 
                    this.setState(
                        update(this.state, {entries: {$push: json.entries}}));
                } else {
                    // replace entries
                    this.setState(json)                    
                }
            });
    }
    
    componentWillMount () {
        console.log("dksoakodk")
        this.fetch(this.props.match.params.logbookId,
                   this.props.location.search,
                   this.state.attributeFilters);
    }
    
    componentWillUpdate (newProps, newState) {
        // if needed, we fetch info from the server
        if ((newProps.match.params.logbookId !==
            this.props.match.params.logbookId ||
             newProps.location.search !== this.props.location.search) ||
            (newState.attributeFilters !== this.state.attributeFilters)) {
            this.fetch(newProps.match.params.logbookId,
                       newProps.location.search,
                       newState.attributeFilters);
        }
        // reset the filters if we've moved to another logbook
        if (newProps.match.params.logbookId !==
            this.props.match.params.logbookId) {
            this.setState(update(this.state, {attributeFilters: {$set: {}}}));
        }             
    }

    componentDidMount () {
        // setup a subscription that makes sure we reload the current
        // logbook whenever e.g. an entry has been added.
        this.props.eventbus.subscribe("logbook.reload", this._reload);
    }

    componentWillUnmount() {
        this.props.eventbus.unsubscribe("logbook.reload", this._reload);
    }

    reload (logbookId) {
        // only need to refresh if we're actually visiting the given logbook
        this.fetch(this.props.match.params.logbookId,
                   this.props.location.search,
                   this.state.attributeFilters);              
    }
    
    componentDidUpdate({match}) {
        // set the browser title
        document.title = `${this.state.logbook.name}`
        // make sure the entry list is scrolled to the top
        if (match.params.logbookId !== this.props.match.params.logbookId)
            findDOMNode(this.refs.entries).scrollIntoView();
    }
    
    onChangeAttributeFilter (attribute, event) {
        // TODO: this should be encoded in the URL search string, like
        // the other search parameters!
        if (event.target.selectedIndex === 0) {
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
        this.fetch(this.props.match.params.logbookId,
                   this.props.location.search,
                   this.state.attributeFilters,
                   this.state.entries.length);
        
        /*         this.fetchMoreEntries();*/
    }
    
    render() {

        const logbook = this.state.logbook,
              entryId = this.props.match.params.entryId?
                        parseInt(this.props.match.params.entryId, 10)
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
                               .filter(attr => attr.type === "option" || attr.type === "multioption")
                               .map(
                                   attr => (
                                       <select key={attr.name} onChange={this.onChangeAttributeFilter.bind(this, attr.name)}>
                                           <option>[{attr.name}]</option>
                                           {attr.options.map((o, i) => <option key={i}>{o}</option>)}
                                       </select>
                                   ))
                         : null;
        const loadMore = this.state.count > this.state.entries.length ?
                         <div onClick={this.onLoadMore.bind(this)}>
                             Load more (showing {this.state.entries.length} of {this.state.count})
                         </div> :
                         null;

        return (
            <div className="container">
                <header>
                    <span className="name">
                        <i className="fa fa-book"/>
                        { logbook.id === 0? "[All logbooks]" : logbook.name }
                    </span>
                    
                    { logbook.id?
                      <div>

                          <div className="entry">
                              <Link to={`/logbooks/${logbook.id}/entries/new`}
                                    title={`Create a new entry in the logbook '${logbook.name}'`}>
                                  New entry
                              </Link>
                          </div>
                          <Link to={`/logbooks/${logbook.id}/?parent=${logbook.id}`}
                                title={`Show only the logbook '${logbook.name}' and it's children`}>
                              Enter
                          </Link> | <Link to={`/logbooks/${logbook.id}/edit`}
                                          title={`Edit the settings of the logbook '${logbook.name}'`}>
                              Edit
                          </Link> | <Link to={`/logbooks/${logbook.id}/new`}
                                          title={`Create a new logbook as a child of '${logbook.name}'`}>
                              New child
                          </Link>
                      </div>
                      : null
                    }
                    <div className="filters"> {filter} </div>
                    <div className="attributes">
                        {attributes}
                    </div>
                </header>
                <div className="entries-container">
                    <div ref="entries">
                        <EntryPreviews logbook={logbook}
                                       entries={this.state.entries}
                                       search={this.props.location.search}
                                       selectedEntryId={entryId}/>
                        <div className="load-more">
                            {
                                this.state.loading?
                                <i className="fa fa-refresh fa-spin"/> :
                                loadMore
                            }
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}


export default Logbook;
