import React from 'react';
import {Link} from 'react-router-dom';

import {EntryPreviews} from './logbook.js';


class SearchResults extends React.Component {

    constructor () {
        super();
        this.state = {entries: []};
    }

    fetchSearchResults (params, logbook) {

        const query = params.search + (logbook? `&logbook=${logbook}` : "");
        
        fetch(`/search/${query}`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState(json));
    }

    componentWillUpdate (newProps) {
        if (newProps.location.search != this.state.search) {
            this.fetchSearchResults(newProps.location,
                                    newProps.match.params.logbook);
            this.setState({search: newProps.location.search});
        }
    }

    /* shouldComponentUpdate (newProps, newState) {
     *     console.log("shouldCompup", newState.search, this.state.search);
     *     return newState.search != this.state.search;
     * }*/
    
    render () {

        const results = this.state.entries.map(entry => (
            <li key={entry.id}>
                <Link to={`/search/logbooks/${entry.logbook}/entries/${entry.id}${this.state.search || ""}`}>
                    {entry.title}
                </Link>
                </li>
        ));
        
        return (
            <div>
                <header>
                    Search
                </header>
                <div>
                    <EntryPreviews logbook={this.props.logbook} entries={this.state.entries} linkPrefix="/search"/>
                </div>
            </div>
        );
    }
}


export default SearchResults;
