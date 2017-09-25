import React from 'react';
import {Link} from 'react-router-dom';

import './logbooktree.css';
import {parseQuery} from './util.js';


class LogbookTreeNode extends React.Component {

    constructor (props) {
        super(props);
        this.state = {
            expanded: false
        };
    }
    
    toggle (event) {
        this.setState({expanded: !this.state.expanded});
    }

    render () {

        const children = (
            this.state.expanded && this.props.children ?
            (<ul>
                {this.props.children.map(
                     child => <LogbookTreeNode
                                  key={child.id}
                                  selectedLogbookId={this.props.selectedLogbookId}
                                  search={this.props.search} {...child}/>)}
            </ul>)
            : null
        );

        const expander = (
            this.props.children.length > 0?
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
        this._reload = this.reload.bind(this);
    }    

    fetch (search) {
        fetch(`/api/logbooks/${search}`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState(json.logbook));
    }        
    
    componentDidMount () {
        this.fetch(this.props.location.search);
        this.props.eventbus.subscribe("logbook.reload", this._reload);
    }

    componentWillReceiveProps ({location}) {
        const query = parseQuery(location.search);
        if ((query.parent || null) !== (this.state.parent || null))
            this.fetch(location.search);
    }
    
    componentWillUnmount() {
        this.props.eventbus.unsubscribe("logbook.reload", this._reload);
    }

    reload () {
        console.log("reload logbook tree");
        this.fetch(this.props.location.search);
    }
    
    render () {

        const logbookId = (this.props.match.params.logbookId?
                           parseInt(this.props.match.params.logbookId, 10)
                         : null);
        const nodes = this.state.children.map(
            logbook => <LogbookTreeNode key={logbook.id}
                                        selectedLogbookId={logbookId}
                                        search={this.props.location.search}
                                        {...logbook}/>);
        const parentId = this.state.parent? (this.state.parent.id || 0) : 0;
        const parentUrl = {
                              pathname:`/logbooks/${parentId}`,
                              search: `parent=${parentId}`
                          };
        
        return (
            <div id="logbooktree">
                <header>
                    <Link to={{
                        pathname: `/logbooks/${this.state.id || 0}`,
                        search: this.props.location.search
                    }}>
                        {this.state.name? this.state.name : "All"}
                    </Link>

                    <div className="commands">
                        {
                            this.state.id?
                            <span>
                                <Link to={ parentUrl } title="Go to the parent logbook" >
                                    Up
                                </Link> |
                            </span>
                            : null
                        }

                        <Link to={`${parentUrl.pathname}/new`}
                              title="Create a new logbook at this level">
                            New
                        </Link>
                    </div>
                    
                </header>
                <div className="tree">
                    {nodes}
                </div>
            </div>
        );
    }    
}


export default LogbookTree;
