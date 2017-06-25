import React from 'react';
import { Route } from 'react-router-dom';
import { parseQuery } from "./util.js";


class QuickSearch extends React.Component {

    constructor () {
        super();
        this.state = {
            content: null,
            title: null,
            authors: null
        }
    }

    onChange (event) {
        this.setState({[event.target.name]: event.target.value});
    }

    onSubmit (history, event) {
        event.preventDefault();  // skip the normal server form submit

        // Some wrangling of query parameters to get a proper search
        // string that we can attach to the location. The point is that
        // keeping all the important state in the URL is good for bookmarking
        // and sharing.
        const query = Object.keys(this.state)
                            .filter(key => this.state[key])
                            .map(key => `${key}=${this.state[key]}`)
                            .join("&");

        // The parent parameter also needs to be kept around because it
        // is used to limit the set of visible logbooks.
        const parent = parseQuery(this.props.location.search)["parent"];
        const parentQuery = parent? `parent=${parent}&` : "";
        history.push({
            pathname: `/logbooks/${this.props.match.params.logbookId || 0}`,
            search: `?${parentQuery}${query}`,
                     state: this.state
        });
    }

    onReset (history, event) {
        this.setState({content: null, title: null, authors: null},
                      this.onSubmit.bind(this, history, event));
    }
    
    render () {

        console.log("search", this.props)
        
        return (
            // This is a slightly ugly way of injecting the browser history
            // into the component so that we can navigate programmatically
            // when the form is submitted...
            <Route render={({history}) => (
                <form id="search" onSubmit={this.onSubmit.bind(this, history)}>

                    <input style={{width: "100%"}} name="title"
                                 value={this.state.title || ""}
                                 type="text" ref="title" placeholder="Title"
                                 onChange={this.onChange.bind(this)}/>
                    <input style={{width: "100%"}} name="content"
                                 value={this.state.content || ""}
                                 type="text" ref="content"
                                 placeholder="Content"      
                                 onChange={this.onChange.bind(this)}/>
                    <input style={{width: "100%"}} name="authors"
                                 value={this.state.authors || ""}
                                 type="text" ref="authors" placeholder="Authors"
                                 onChange={this.onChange.bind(this)}/>
                    
                    <input type="submit" value="Search"/>
                    <input type="button" value="Clear" onClick={this.onReset.bind(this, history)}/>
                </form>
            )}/>
        );
    }    
}


export default QuickSearch;
