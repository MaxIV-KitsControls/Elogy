/*
   This component shows a form for editing a single entry
*/

import React from 'react';
import {Link, Route, Prompt} from 'react-router-dom';
import update from 'immutability-helper';
import TinyMCEInput from './TinyMCEInput.js';
import {Select, Creatable, AsyncCreatable, Async} from 'react-select';
import Dropzone from 'react-dropzone'
import 'react-select/dist/react-select.css';

import "./entryeditor.css";
import { EntryAttachments } from "./entryattachments.js";
import EventSystem from "./eventsystem.js";
import TINYMCE_CONFIG from "./tinymceconfig.js";


class EntryAttributeEditor extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            value: props.value
        }
    }

    onChange (event) {
        this.setState({value: event.target.value});
    }

    onChangeBoolean (event) {
        this.setState({value: event.target.checked});
    }
    
    onChangeSelect (value) {
        this.setState({value: value.value})
    }    

    onChangeMultiSelect (value) {
        this.setState({value: value.map(o => o.value)});
    }

    onBlur () {
        this.props.onChange(this.props.config.name, this.state.value);
    }
    
    makeInputElement () {
        const required = this.props.config.required;
        switch(this.props.config.type) {
            case "text":
                return <input type="text" value={this.state.value}
                              ref="attr" required={required}
                              onChange={this.onChange.bind(this)}
                              onBlur={this.onBlur.bind(this)}/>;
            case "number":
                return <input type="text" value={this.state.value}
                              ref="attr" required={required}
                              onChange={this.onChange.bind(this)}
                              onBlur={this.onBlur.bind(this)}/>;
            case "boolean":
                return <input type="checkbox" checked={this.state.value}
                              ref="attr" required={required}
                              onChange={this.onChangeBoolean.bind(this)}
                              onBlur={this.onBlur.bind(this)}/>;
            case "option":
                return <Creatable value={this.state.value}
                                  required={required}
                                  options={this.props.config.options.map(o => {return {value: o, label: o}})}
                                  onChange={this.onChangeSelect.bind(this)}
                                  onBlur={this.onBlur.bind(this)}/>;
            case "multioption":
                return <Creatable value={this.state.value} multi={true}
                                  required={required}
                                  options={this.props.config.options.map(o => {return {value: o, label: o}})}
                                  onChange={this.onChangeMultiSelect.bind(this)}
                                  onBlur={this.onBlur.bind(this)}/>;
        }
    }
                
    render () {
        const className = `attribute-wrapper ${this.props.config.type}-attribute`;
        return (
            <div className={className}>
                {this.makeInputElement()}
            </div>
        )
    }
}


class EntryEditor extends React.Component {

    constructor (props) {
        super(props);
        this.state = {
            submitted: false,
            id: null,
            logbook: {},
            title: "",
            authors: [],
            attributes: {},
            attachments: [],
            content: null
        }
    }

    fetchEntry (logbookId, entryId) {
        fetch(`/api/entries/${entryId}/`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState({entry: json, ...json}));        
    }

    fetchLogbook (logbookId) {
        fetch(`/api/logbooks/${logbookId}`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState({logbook: json}));        
    }
    
    componentWillMount () {
        if (this.props.match.params.entryId) {
            if (this.props.match.url.split("/").slice(-1)[0] === "edit") {
                this.fetchEntry(this.props.match.params.logbookId,
                                this.props.match.params.entryId);
            } else {
                this.setState({follows: parseInt(this.props.match.params.entryId)});
                this.fetchLogbook(this.props.match.params.logbookId);
            }
        } else {
            this.fetchLogbook(this.props.match.params.logbookId);
        }
    }

    onTitleChange (event) {
        this.setState({title: event.target.value});
    }

    fetchUserSuggestions (input) {
        return fetch(`/api/users`, 
              {
                  headers: {"Accept": "application/json"}
              })
            .then(response => response.json())
            .then(response => {return {
                options: (this.state.authors
                              .concat(response.users)),
                complete: false
            }});
    }
    
    onAuthorsChange (newAuthors) {
        this.setState({authors: newAuthors});
    }

    onAttributeChange (name, value) {
        console.log("onAttributeChange", name, value);
        this.setState(update(this.state, {attributes: {[name]: {$set: value}}}));
    }
    
    onContentChange (event) {
        this.setState({content: event.target.getContent()});
    }

    onAddAttachment (acceptedFiles, rejectedFiles) {
        console.log("drop", acceptedFiles, rejectedFiles);
        this.setState(update({newAttachments: {$push: acceptedFiles}}))
    }

    hasEdits () {
        const original = this.state.entry || {};
        return (!this.submitted &&
                (this.state.title != original.title ||
                 this.state.content != original.content ||
                 this.state.authors != original.authors));
    }

    getPromptMessage () {
        /* This is a little confusing, but the <Prompt> component will
           only show a prompt if this function returns a message. */        
        if (this.hasEdits())
            return "Looks like you have made some edits. If you leave, you will lose those...";
    }
        
    onSubmit(history) {
        this.submitted = true;
        if (this.state.id > 0) {
            // we're editing an existing entry
            fetch(`/api/logbooks/${this.state.logbook.id}/entries/${this.state.id}/`, 
                  {
                      method: "PUT",
                      headers: {
                          'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                          id: this.state.id,
                          follows: this.state.follows,
                          title: this.state.title,
                          authors: this.state.authors,
                          content: this.state.content || this.state.logbook.template,
                          attributes: this.state.attributes
                      })
                  })
                .then(response => response.json())
            // TODO: handle errors 
                .then(response => {
                    EventSystem.publish("logbook.reload", this.state.logbook.id);
                    history.push({
                        // send the browser to the entry
                        pathname: `/logbooks/${this.state.logbook.id}/entries/${this.state.id}`

                    });
                    
                });
        } else {
            // we're creating a new entry
            const followupTo = (this.props.match.params.entryId?
                                parseInt(this.props.match.params.entryId)
                              : null)
            fetch(`/api/logbooks/${this.state.logbook.id}/entries`, 
                  {
                      method: "POST",
                      headers: {
                          'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                          follows: this.state.follows,
                          title: this.state.title,
                          authors: this.state.authors,
                          content: this.state.content || this.state.logbook.template,
                          attributes: this.state.attributes
                      })
                  })
                .then(response => response.json())
            // TODO: handle errors 
                .then(response => {
                    history.push({
                        pathname: `/logbooks/${this.state.logbook.id}/entries/${response.entry_id}`,
                        state: {
                            entrySubmitted: true
                        }
                    });
                    EventSystem.publish("logbook.reload", this.state.logbook.id);
                });
        }
    }

    renderInner ({history}) {

        // we need the router 'history' object injected here so that
        // we can automatically send the browser to the entry after submitting.

        let title;
        if (this.state.entry) {
            title = <span className="title">
                Editing entry <span className="entry">{this.state.entry.title}</span> in <span className="logbook"> <i className="fa fa-book"/> {this.state.logbook.name}</span>
            </span>
        } else {
            title = <span className="title">
                New entry in <span className="logbook"> <i className="fa fa-book"/>{this.state.logbook.name}</span>
            </span>
        }
        
        const attributes = this.state.logbook.attributes?
        this.state.logbook.attributes
        .map((attr, i) => (
        <span key={i}>
            <label>
                {attr.name}
                <EntryAttributeEditor
                    config={attr} 
                    onChange={this.onAttributeChange.bind(this)}
                    value={this.state.attributes[attr.name]}/>
            </label>
        </span>
        ))
        : null;

        const cancel = this.state.entry?
                       <Link to={`/logbooks/${this.state.logbook.id}/entries/${this.state.entry.id}`}>
                           Cancel
                       </Link> :
                       <Link to={`/logbooks/${this.state.logbook.id}/`}>
                           Cancel
                       </Link>;
                       
        return (
            <div id="entryeditor">

                <Prompt message={this.getPromptMessage.bind(this)}/>
                
                <header>
                    { title }
                    <input type="text" placeholder="title"
                           value={this.state.title} required={true}
                           onChange={this.onTitleChange.bind(this)}/>
                    <Async
                        name="authors" placeholder="Authors"
                        valueRenderer={o => o.name}
                        multi={true} value={this.state.authors}
                        optionRenderer={o => `${o.login} [${o.name}]`}
                        valueKey="login" labelKey="name"
                        options={this.state.authors}
                        loadOptions={this.fetchUserSuggestions.bind(this)}
                        onChange={this.onAuthorsChange.bind(this)}
                    />
                    
                    <div className="attributes">
                        {attributes}
                    </div>
                    
                </header>
                <div className="content">
                    <TinyMCEInput
                        value={this.state.content || this.state.logbook && this.state.logbook.template || ""}
                        tinymceConfig={ TINYMCE_CONFIG }
                        onBlur={this.onContentChange.bind(this)}/>
                </div>
                <footer>
                    <Dropzone onDrop={this.onAddAttachment.bind(this)}
                              className="attachments-drop">
                        Attachments
                        <EntryAttachments attachments={this.state.attachments}/>
                    </Dropzone>
                    
                    <button onClick={this.onSubmit.bind(this, history)}>
                        Submit
                    </button>
                    <div className="commands">
                        { cancel }
                    </div>
                </footer>
            </div>
        );
    }

    render () {
        return <Route render={this.renderInner.bind(this)}/>;
    }
    
}


export default EntryEditor;
