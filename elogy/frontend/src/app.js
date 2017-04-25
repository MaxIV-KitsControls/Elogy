import React from 'react';
import './app.css';
import Entry from './entry.js';
import EntryEditor from './entryeditor.js';
import Logbook from './logbook.js';
import LogbookEditor from './logbookeditor.js';
import LogbookTree from './logbooktree.js';
import QuickSearch from './search.js';
import SearchResults from './searchresults.js';

import {
    BrowserRouter as Router,
    Route, Switch,
    Link
} from 'react-router-dom'


const Elogy = () => (

    <Router>
        <div id="app">
            
            <div id="logbooks">
                <Switch>
                    <Route path="/logbooks/:logbookId"
                           component={LogbookTree}/>
                    <Route component={LogbookTree}/>
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
                           component={Logbook}/>                        
                    <Route path="/logbooks/:logbookId"
                           component={Logbook}/>
                </Switch>
            </div>

            <div id="entry">
                <Switch>
                    <Route path="/logbooks/:logbookId/edit"
                           component={LogbookEditor}/>
                    <Route path="/logbooks/:logbookId/new"
                           component={LogbookEditor}/>
                    
                    <Route path="/entries/:entryId"
                           component={Entry}/>

                    <Route path="/logbooks/:logbookId/entries/new"
                           component={EntryEditor}/>
                    <Route path="/logbooks/:logbookId/entries/:entryId/edit"
                           component={EntryEditor}/>
                    <Route path="/logbooks/:logbookId/entries/:entryId"
                           component={Entry}/>
                </Switch>
            </div>
            
        </div>
    </Router>
)


export default Elogy
