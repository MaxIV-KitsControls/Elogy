import React from 'react';
import {
    BrowserRouter as Router,
    Route, Switch,
    Link
} from 'react-router-dom'

import Entry from './entry.js';
import EntryEditor from './entryeditor.js';
import Logbook from './logbook.js';
import LogbookEditor from './logbookeditor.js';
import LogbookTree from './logbooktree.js';
import QuickSearch from './search.js';
import SearchResults from './searchresults.js';
import EventBus from './eventsystem.js';
import './app.css';


// A common eventbus that allows simple communication between
// components. Should only be used for simple things like
// asking a component to reload. If we start using it for passing
// data around we'd better switch to Redux or something.
const eventbus = new EventBus();


// "bind" the given properties statically to a component
export function withProps (Comp, extraProps) {
    return (props) => <Comp {...props} {...extraProps}/>;
}


const Elogy = () => (

    <Router>
        <div id="app">
            
            <div id="logbooks">
                <Switch>
                    <Route path="/logbooks/:logbookId"
                           component={withProps(LogbookTree, {eventbus})}/>
                    <Route component={withProps(LogbookTree, {eventbus})}/>
                </Switch>
                <Switch>
                    <Route path="/logbooks/:logbookId"
                           component={QuickSearch}/>
                    <Route component={QuickSearch}/>
                </Switch>                            
            </div>
            
            <div id="logbook">
                <Switch>                            
                    <Route path="/logbooks/:logbookId/entries/:entryId"
                           component={withProps(Logbook, {eventbus})}/>
                    <Route path="/logbooks/:logbookId"
                           component={withProps(Logbook, {eventbus})}/>
                </Switch>
            </div>

            <div id="entry">
                <Switch>

                    <Route path="/logbooks/:logbookId/entries/new"
                           component={withProps(EntryEditor, {eventbus})}/>
                    <Route path="/logbooks/:logbookId/entries/:entryId/:command"
                           component={withProps(EntryEditor, {eventbus})}/>
                    
                    <Route path="/logbooks/:logbookId/entries/:entryId"
                           component={Entry}/>
                    <Route path="/entries/:entryId"
                           component={Entry}/>

                    <Route path="/logbooks/new"
                           component={withProps(LogbookEditor, {eventbus})}/>
                    <Route path="/logbooks/:logbookId/:command"
                           component={withProps(LogbookEditor, {eventbus})}/>
                    
                </Switch>
            </div>
            
        </div>
    </Router>
)


export default Elogy
