/*
   This component shows a form for editing a single entry
*/

import React from 'react';
import {Link, Route} from 'react-router-dom';
import update from 'immutability-helper';
/* import TinyMCE from 'react-tinymce';*/
import TinyMCEInput from './TinyMCEInput.js';
import {Select, Creatable, AsyncCreatable, Async} from 'react-select';
import Dropzone from 'react-dropzone'
import 'react-select/dist/react-select.css';

import "./entryeditor.css";
import { EntryAttachments } from "./entryattachments.js";
import EventSystem from "./eventsystem.js";


class EntryAttributeEditor extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            value: props.value
        }
    }

    onChange (event) {
        this.setState({value: event.target.value});
        /*         this.props.onChange(this.props.config.name, event.target.value);*/
    }

    onChangeBoolean (event) {
        this.setState({value: event.target.checked});
        /*         this.props.onChange(this.props.config.name, event.target.value);*/
    }
    
    onChangeSelect (value) {
        this.setState({value: value.value})
        /*         this.props.onChange(this.props.config.name, value.value);*/
    }    

    onChangeMultiSelect (value) {
        this.setState({value: value.map(o => o.value)});
    }

    onBlur () {
        this.props.onChange(this.props.config.name, this.state.value);
    }
    
    makeInputElement () {
        switch(this.props.config.type) {
            case "text":
                return <input type="text" value={this.state.value}
                              ref="attr"
                              onChange={this.onChange.bind(this)}
                              onBlur={this.onBlur.bind(this)}/>;
            case "number":
                return <input type="text" value={this.state.value}
                              ref="attr"
                              onChange={this.onChange.bind(this)}
                              onBlur={this.onBlur.bind(this)}/>;
            case "boolean":
                return <input type="checkbox" checked={this.state.value}
                              ref="attr"
                              onChange={this.onChangeBoolean.bind(this)}
                              onBlur={this.onBlur.bind(this)}/>;
            case "option":
                return <Creatable value={this.state.value}
                                  options={this.props.config.options.map(o => {return {value: o, label: o}})}
                                  onChange={this.onChangeSelect.bind(this)}
                                  onBlur={this.onBlur.bind(this)}/>;
            case "multioption":
                return <Creatable value={this.state.value} multi={true}
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
                options: (this.state.authors.map(a => {return {value: a, label: a}})
                              .concat(response.users.map(u => {return {value: u.login, label: u.name}}))),
                complete: false
            }});
    }
    
    onAuthorsChange (newAuthors) {
        this.setState({authors: newAuthors.map(a => a.value)});
    }

    onAttributeChange (name, value) {
        console.log("onAttributeChange", name, value);
        this.setState(update(this.state, {attributes: {[name]: {$set: value}}}));
    }
    
    onContentChange (value) {
        this.setState({content: value});
    }

    onAddAttachment (acceptedFiles, rejectedFiles) {
        console.log("drop", acceptedFiles, rejectedFiles);
        this.setState(update({newAttachments: {$push: acceptedFiles}}))
    }

    onSubmit(history) {
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
                            reloadLogbook: true  // tell other components to refresh logbook info
                        }
                    });
                    EventSystem.publish("logbook.reload", this.state.logbook.id);
                });
        }
    }

    renderInner ({history}) {

        // we need the router 'history' object injected here so that
        // we can automatically send the browser to the entry after submitting.

        
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
        
        return (
            <div id="entryeditor">
                <header>
                    {
                        this.state.title?
                        <span className="old-title">
                            Editing entry <span>{this.state.title}</span> in <span>{this.state.logbook.name}</span>
                        </span>
                        : <span>New entry in <span>{this.state.logbook.name}</span></span>
                    }   
                    <input type="text" placeholder="title"
                           value={this.state.title} required={true}
                           onChange={this.onTitleChange.bind(this)}/>
                    <Async
                        name="authors" placeholder="Authors"
                        valueRenderer={o => o.label}
                        multi={true} value={this.state.authors}
                        optionRenderer={o => `${o.label} [${o.value}]`}
                        options={this.state.authors.map(a => {return {value: a, label: a}})}
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
                         tinymceConfig={{
                             plugins: "link image textcolor paste table lists advlist code",
                             toolbar: (
                                 "undo redo | removeformat | styleselect |"
                                 + " bold italic forecolor backcolor |"
                                 + " bullist numlist outdent indent | link image table | code"
                             ),
                             menubar: false,
                             statusbar: false,
                             content_css: "/static/tinymce-tweaks.css",
                             height: "100%",
                             relative_urls : false,  // otherwise images broken in editor
                             apply_source_formatting: false,
                             force_br_newlines: false,
                             paste_data_images: true,
                             //          automatic_uploads: false,  // don't immediately upload images
                             //images_upload_handler: customUploadHandler,
                             image_dimensions: false,
                             forced_root_block : "",
                             cleanup: true,
                             force_p_newlines : true,                             
                             convert_newlines_to_brs: false,                             
                             inline_styles : false,
                             entity_encoding: 'raw',
                             entities: '160,nbsp,38,amp,60,lt,62,gt',
                             resize: true,
                             theme: "modern"
                         }}
                         onChange={this.onContentChange.bind(this)}/>
                </div>
                <footer>
                    <Dropzone onDrop={this.onAddAttachment.bind(this)}
                              className="attachments-drop">
                        Attachments
                        <EntryAttachments attachments={this.state.attachments}/>
                    </Dropzone>
                    
                    <button onClick={this.onSubmit.bind(this, history)}>Submit</button>
                </footer>
            </div>
        );
    }

    render () {
        return <Route render={this.renderInner.bind(this)}/>;
    }
    
}


export default EntryEditor;
