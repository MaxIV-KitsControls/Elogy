/*
   This component shows a form for editing a single entry
*/

import React from 'react';
import {Link, Route} from 'react-router-dom';
import update from 'immutability-helper';
import TinyMCE from 'react-tinymce';
import {Select, Creatable, AsyncCreatable, Async} from 'react-select';
import Dropzone from 'react-dropzone'
import 'react-select/dist/react-select.css';

import "./entryeditor.css";
import { EntryAttachments } from "./entry.js";


class EntryAttributeEditor extends React.Component {

    onChange () {
        this.props.onChange(this.props.config.name, this.event.target.value);
    }

    onChangeSelect (value) {
        this.props.onChange(this.props.config.name, value.value);
    }    

    onChangeMultiSelect (value) {
        this.props.onChange(this.props.config.name, value.map(o => o.value));
    }    
    
    makeInputElement () {
        switch(this.props.config.type) {
            case "text":
                return <input type="text" value={this.props.value}
                              ref="attr"
                              onChange={this.onChange.bind(this)}/>;
            case "number":
                return <input type="text" value={this.props.value}
                              ref="attr"
                              onChange={this.onChange.bind(this)}/>;
            case "boolean":
                return <input type="checkbox" checked={this.props.value}
                              ref="attr"
                              onChange={this.onChange.bind(this)}/>;
            case "option":
                return <Creatable value={this.props.value}
                                  options={this.props.config.options.map(o => {return {value: o, label: o}})}
                                  onChange={this.onChangeSelect.bind(this)}/>;
            case "multioption":
                return <Creatable value={this.props.value} multi={true}
                                  options={this.props.config.options.map(o => {return {value: o, label: o}})}
                                  onChange={this.onChangeMultiSelect.bind(this)}/>;
        }
    }
                
    render () {
        return (
            <div className="select-wrapper">
                {this.makeInputElement()}
            </div>
        )
    }
}


class EntryEditor extends React.Component {

    constructor (props) {
        super(props);
        this.state = {
            id: 0,
            logbook: {},
            title: "",
            authors: [],
            attributes: {},
            attachments: [],
            newAttachments: [],
            content: null
        }
    }

    fetchEntry (logbookId, entryId) {
        fetch(`/api/entries/${entryId}/`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState(json));        
    }

    fetchLogbook (logbookId) {
        fetch(`/api/logbooks/${logbookId}`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState({logbook: json}));        
    }
    
    componentWillMount () {
        if (this.props.match.params.entryId)
            this.fetchEntry(this.props.match.params.logbookId,
                            this.props.match.params.entryId);
        else
            this.fetchLogbook(this.props.match.params.logbookId);
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
    
    onContentChange (event) {
        this.setState({content: event.target.getContent()});
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
                          title: this.state.title,
                          authors: this.state.authors,
                          content: this.state.content,
                          attributes: this.state.attributes
                      })
                  })
                .then(response => response.json())
            // TODO: handle errors 
                .then(response => history.push({
                    // send the browser to the entry
                    pathname: `/logbooks/${this.state.logbook.id}/entries/${this.state.id}`
                }));
        } else {
            // we're creating a new entry
            fetch(`/api/logbooks/${this.state.logbook.id}/entries`, 
                  {
                      method: "POST",
                      headers: {
                          'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                          title: this.state.title,
                          authors: this.state.authors,
                          content: this.state.content,
                          attributes: this.state.attributes
                      })
                  })
                .then(response => response.json())
            // TODO: handle errors 
                .then(response => history.push({
                    pathname: `/logbooks/${this.state.logbook.id}/entries/${response.entry}`,
                    state: {
                        reloadLogbook: true  // tell other components to refresh logbook info
                    }
                }));
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
                    <input type="text" value={this.state.title}
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
                    {this.state.content?
                        <TinyMCE
                            content={this.state.content}
                            config={{
                                plugins: 'link image code',
                                plugins: "image textcolor paste table lists advlist code",
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
                                remove_linebreaks: true,
                                convert_newlines_to_brs: false,
                                inline_styles : false,
                                entity_encoding: 'raw',
                                entities: '160,nbsp,38,amp,60,lt,62,gt'         
                            }}
                            onChange={this.onContentChange.bind(this)}/>
                        :null}
                </div>
                <Dropzone onDrop={this.onAddAttachment.bind(this)}
                          className="attachments-drop">
                    <EntryAttachments attachments={this.state.attachments}/>
                </Dropzone>
                <footer>
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
