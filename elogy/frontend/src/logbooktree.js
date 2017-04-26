import React from 'react';
import {Link} from 'react-router-dom';

import './logbooktree.css';
import {parseQuery} from './util.js';


class LogbookTreeNode extends React.Component {

    /* TODO: this is pretty inefficient since it always fetches
       children to visible logbooks even if they are never expanded.
       Instead we should be lazy and only fetch children as needed.
     */
    
    constructor () {
        super();
        this.state = {
            children: [],
            expanded: false
        };
    }

    fetchLogbooks() {
        fetch("/api/logbooks/" + (this.props.id || ""),
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState(json));        
    }

    componentWillMount (newProps, newState) {
        this.fetchLogbooks();
    }
    
    toggle (event) {
        this.setState({expanded: !this.state.expanded});
    }

    shouldComponentUpdate (newProps, newState) {
        return (newState.logbooks != this.state.logbooks ||
                newState.expanded != this.state.expanded ||
                newProps.selectedLogbookId != this.props.selectedLogbookId
        )
    }
    
    render () {

        console.log("node", this.props);
        
        const children = (
            this.state.expanded && this.state.children?
            (<ul>
    {this.state.children.map(
         child => <LogbookTreeNode key={child.id}
                                   selectedLogbookId={this.props.selectedLogbookId}
                                   search={this.props.search} {...child}/>)}
            </ul>)
            : null
        );

        const expander = (
            this.props.n_children > 0?
            (
                <span>
                    <input type="checkbox" checked={this.state.expanded}
                           id={`check-${this.props.id}`}
                           onClick={this.toggle.bind(this)}/> 
                    <label htmlFor={`check-${this.props.id}`}></label>
                </span>
            )
            : null
        );

        // make sure we keep any parent setting 
        const query = parseQuery(this.props.search);
        const parentQuery = query.parent? `?parent=${query.parent}` : "";
        
        return (
            <li key={this.props.id}
                title={this.props.description || null}
                className={
                    (this.props.selectedLogbookId === this.props.id? "selected " : "") +
                     (this.state.n_children > 0? "has-children" : "")
                          }>
                { expander }
                <Link to={`/logbooks/${this.props.id}${parentQuery}`}>
                    { this.props.name }
                </Link>
                { children }
            </li>
        );
    }
}


class LogbookTree extends React.Component {

    constructor () {
        super();
        this.state = {
            parent: null,
            children: []
        };
    }    

    fetchLogbooks (search) {
        fetch(`/api/logbooks/${search}`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState(json));
    }        
    
    componentDidMount () {
        this.fetchLogbooks(this.props.location.search);
    }
    
    render () {

        const logbookId = (this.props.match.params.logbookId?
                           parseInt(this.props.match.params.logbookId)
                         : null);
        console.log("tree", this.state);

        const nodes = this.state.children.map(
            logbook => <LogbookTreeNode key={logbook.id}
                                        selectedLogbookId={logbookId}
                                        search={this.props.location.search}
                                        {...logbook}/>);
        
        return (
            <div id="logbooktree">
                <header>
                    <Link to={`/logbooks/${this.state.id}?parent=${this.state.id}`}>
                        {this.state.name? this.state.name : "All"}
                    </Link>

                    <div className="commands">
                        <Link to={`/logbooks/${this.state.parent? this.state.parent.id : 0}/new`}>
                            New
                        </Link>
                    </div>
                    
                    {
                        this.state.id?
                        <span>
                            
                            <Link to={`/logbooks/${this.state.parent.id || 0}?parent=${this.state.parent.id || 0}`}>Up</Link>
                        </span>
                        : null
                    }
                </header>
                <div className="tree">
                    {nodes}
                </div>
            </div>
        );
    }
    
}


export default LogbookTree;
