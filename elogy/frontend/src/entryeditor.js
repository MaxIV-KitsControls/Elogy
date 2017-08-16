/* This component shows a form for editing a single entry. It may be
   creating a new entry, making a followup to another entry or
   modifying an existing entry.  */

/* 
   TODO: there's quite a lot of repeated functionality here, that
   should probably be refactored to be re-used more. Also, maybe
   all the little "get*" helpers should be moved into separate
   components.
*/

import React from 'react';
import {Link, Route, Prompt, Switch} from 'react-router-dom';
import update from 'immutability-helper';
import TinyMCEInput from './TinyMCEInput.js';
import Select from 'react-select';
import {Creatable, Async} from 'react-select';
import Dropzone from 'react-dropzone'
import 'react-select/dist/react-select.css';

import { EntryAttachments } from "./entryattachments.js";
import TINYMCE_CONFIG from "./tinymceconfig.js";
import {withProps, debounce} from './util.js';
import { InnerEntry } from "./entry.js";
import "./entryeditor.css";


class EntryAttributeEditor extends React.Component {

    /* editor for a single attribute */
    
    constructor(props) {
        super(props);
        this.state = {
            value: props.value
        }
    }

    onChange (event) {
        this.setState({value: event.target.value});
    }

    onKeypressNumber (event) {
        // very primitive validity checking...
        if (!(event.key === "." || parseInt(event.key, 10)))
            event.preventDefault();
    }
    
    onChangeBoolean (event) {
        this.setState({value: event.target.checked});
    }
    
    onChangeSelect (value) {
        this.setState({value: value? value.value : null})
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
                return <input type="text" value={ this.state.value }
                              ref="attr" required={ required }
                              onChange={ this.onChange.bind(this) }
                              onBlur={ this.onBlur.bind(this) }/>;
            case "number":
                return <input type="number" step="any" inputmode="numeric"
                              value={ this.state.value }
                              ref="attr" required={ required }
                              onKeyPress={ this.onKeypressNumber }
                              onChange={ this.onChange.bind(this) }
                              onBlur={ this.onBlur.bind(this) }/>;
            case "boolean":
                return <input type="checkbox" checked={ this.state.value }
                              ref="attr" required={ required }
                              onChange={ this.onChangeBoolean.bind(this) }
                              onBlur={ this.onBlur.bind(this) }/>;
            case "option":
                // Note: use <Creatable> here instead, to allow creating
                // new options directly from the dropdown. Requires more
                // machinery here though, to modify the logbook attribute.
                return <Select value={ this.state.value }
                               required={ required }
                               options={ this.props.config.options.map(
                                       o => {return {value: o, label: o}}) }
                               onChange={ this.onChangeSelect.bind(this) }
                               onBlur={ this.onBlur.bind(this) }/>;
            case "multioption":
                return <Select value={ this.state.value } multi={ true }
                               required={ required }
                               options={ this.props.config.options.map(
                                       o => {return {value: o, label: o}}) }
                               onChange={ this.onChangeMultiSelect.bind(this) }
                               onBlur={ this.onBlur.bind(this) }/>;
            default:
                return <div>?</div>
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


class EntryEditorBase extends React.Component {

    /* common functionality for all entry editor variants */

    constructor (props) {
        super(props);
        this.state = {
            id: null,
            logbook: null,
            title: null,
            authors: [],
            attributes: {},
            attachments: [],
            metadata: {},
            content: null,
            priority: 0,
            lock: null,
            error: null
        }
        // we don't want to stress the backend by searching for users
        // at every keystroke so we'll limit the rate a little.
        this.slowFetchUserSuggestions = debounce(this.fetchUserSuggestions.bind(this), 500);
    }

    fetchEntry (logbookId, entryId, fill) {
        // get all data for the given entry from the backend
        fetch(`/api/logbooks/${logbookId}/entries/${entryId}/`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => {
                if (fill)
                    this.setState({entry: json.entry, ...json.entry});
                else
                    this.setState(json);
            });
    }

    fetchLogbook (logbookId) {
        // get data for the given logbook from the backend
        fetch(`/api/logbooks/${logbookId}/`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => this.setState(json));        
    }

    fetchUserSuggestions (input, callback) {
        // search for author names
        return fetch(`/api/users/?search=${input}`, 
                     {
                         headers: {"Accept": "application/json"}
                     })
            .then(response => response.json())
            .then(response => {
                callback(null, {
                    options: ((this.state.authors || [])
                                  .concat(response.users)),
                    complete: false
                });
            });
    }

    onTitleChange (event) {
        this.setState({title: event.target.value});
    }
    
    onAuthorsChange (newAuthors) {
        this.setState({authors: newAuthors});
    }

    onAttributeChange (name, value) {
        console.log("onAttributeChange", name, value);
        this.setState(update(this.state, {attributes: {[name]: {$set: value}}}));
        /* else
         *     this.setState(update(this.state, {attributes: {$unset: [name]}}));*/
    }
    
    onContentChange (event) {
        console.log("set content", event.target.getContent());
        this.setState({content: event.target.getContent()});
    }
    
    onAddAttachment (acceptedFiles, rejectedFiles) {
        console.log("drop", acceptedFiles, rejectedFiles);
        this.setState(update(this.state, {attachments: {$push: acceptedFiles}}))
    }
    
    onTogglePinned (event) {
        this.setState({priority: (event.target.checked? 100 : 0)});
    }
    
    hasEdits () {
        // return whether the user had edited anything or not
        const original = this.state.entry || {};
        return (!this.submitted &&
                (this.state.title !== original.title ||
                 this.state.content !== original.content ||
                 this.state.authors !== original.authors));
    }

    getPromptMessage () {
        /* This is a little confusing, but the <Prompt> component will
           only show a prompt if this function returns a message. */        
        if (this.hasEdits())
            return "Looks like you have made some edits. If you leave, you will lose those...";
    }

    getTitleEditor (title) {
        return (<input type="text" className="title" placeholder="Title for the new entry..."
                       ref="title"
                       value={title || ""} required={true}
                       onChange={this.onTitleChange.bind(this)}/>);

    }

    getAuthorsEditor (authors) {
        return <Async
                   name="authors" placeholder="Authors" ref="authors"
                   valueRenderer={o => o.name}
                   multi={true}
                   value={ authors }
                   optionRenderer={o => `${o.login} [${o.name}]`}
                   valueKey="login" labelKey="name"
                   options={ authors }
                   loadOptions={ this.slowFetchUserSuggestions.bind(this) }
                   onChange={ this.onAuthorsChange.bind(this) }
                   ignoreAccents={false}
        />
    }
        
    getContentHTMLEditor (content) {
        return (
            <TinyMCEInput
                value={ content || "" }
                tinymceConfig={ TINYMCE_CONFIG }
                onBlur={ this.onContentChange.bind(this) }/>            
        );
    }

    getAttributes () {
        if (Object.keys(this.state.attributes).length > 0) {
            return this.state.attributes;
        } else {
            if (this.state.entry)
                return this.state.entry.attributes;
            return {}
        }
    }
    
    getAttributesEditors (attributes) {
        return this.state.logbook.attributes?
               this.state.logbook.attributes
                   .map((attr, i) => (
                       <span key={i}>
                           <label>
                               {attr.name}
                               <EntryAttributeEditor
                                   config={attr} 
                                   onChange={this.onAttributeChange.bind(this)}
                                   value={ attributes[attr.name] }/>
                           </label>
                       </span>
                   ))
             : null;
    }

    getAttachments (attachments) {
        return (
            <Dropzone onDrop={this.onAddAttachment.bind(this)}
                      title="Click (or drag-and-drop) to add attachments."
                      className="attachments-drop">
                {
                    attachments.length > 0 ?
                    <EntryAttachments attachments={ attachments }/> :
                    "Drop attachments here (or click)!"
                }
            </Dropzone>
        );
    }

    getSubmitButton (history) {
        return (
            <button className="submit"
                    title="Upload the entry"
                    onClick={this.onSubmit.bind(this, history)}>
                Submit
            </button>
        );
    }

    getPinnedCheckbox () {
        return (
            <label title="The entry will stay at the top of the logbook.">
                <input type="checkbox"
                       checked={this.state.priority > 0}
                       onChange={this.onTogglePinned.bind(this)}/>
                Pinned
            </label>
        );
    }

    onPriorityChange (event) {
        console.log("onPriorityChange", event.target.value);
        this.setState({priority: event.target.value});
    }

    getPriority () {
        const priority = this.state.priority;
        if (priority === 0)
            return 0;
        if (priority > 0 && priority <= 100) {
            return 100;
        }
        if (priority > 100 && priority <= 200) {
            return 200;
        }
    }

    getPrioritySelector () {
        return (
            <label>
                Priority
                <select
                    value={this.getPriority()}
                    onChange={this.onPriorityChange.bind(this)}>
                    <option value={200}
                            title="The entry will be sorted before normal and pinned entries, and also visible in all descendant logbooks.">
                        Important
                    </option>
                    <option value={100}
                            title="The entry will be sorted before normal entries.">
                        Pinned
                    </option>
                    <option value={0}>Normal</option>
                </select>
            </label>
        );
    }
    
    getCancelButton () {
        return this.state.entry?
               <Link to={`/logbooks/${this.state.logbook.id}/entries/${this.state.entry.id}`}
                     title="Abandon edits without uploading.">
                   <button className="cancel">Cancel</button>
               </Link> :
               <Link to={`/logbooks/${this.state.logbook.id}/`}
                     title="Abandon edits without uploading.">
                   <button className="cancel">Cancel</button>
               </Link>;
    }

    getError () {
        if (this.state.error) {
            return <span className="error">Error: {JSON.stringify(this.state.error.messages)}</span>
        } else {
            return null;
        }
    }    

    submitAttachments (entryId) {
        return this.state.attachments.map(attachment => {
            // TODO: also allow removing attachments            
            if (!(attachment instanceof File)) {
                // this attachment is already uploaded
                // TODO: do this in a nicer way
                return null;
            }
            let data = new FormData()
            data.append("attachment", attachment);
            return fetch(`/api/logbooks/${this.state.logbook.id}/entries/${entryId}/attachments/`,
                         {method: "POST", body: data});
        });
    }

    render () {
        // we need to wrap up the rendered component in a Route in order
        // to have access to the "history" object for submitting.
        // Each subclass should implement a "innerRender" method that
        // renders as usual.
        return <Route render={this.renderInner.bind(this)}/>;
    }
}


class EntryEditorNew extends EntryEditorBase {

    /* editor for creating a brand new entry */

    componentWillMount () {
        this.fetchLogbook(this.props.match.params.logbookId);
    }
    
    onSubmit({history}) {
        this.submitted = true;
        // we're creating a new entry
        fetch(
            `/api/logbooks/${this.state.logbook.id}/entries/`, {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: this.state.title,
                    authors: this.state.authors,
                    content: this.state.content,
                    content_type: this.state.content_type,
                    attributes: this.state.attributes,
                    follows_id: this.state.follows,
                    archived: this.state.archived,
                    metadata: this.state.metadata,
                    priority: this.state.priority
                })
            })
            .then(response => {
                if (response.ok) {
                    return response.json()
                }
                // something went wrong!
                // TODO: error handling probably needs some work.
                response.json().then(
                    error => {this.setState({error: error})},
                    error => {this.setState({error: {message: response.statusText,
                                                     code: response.status}})}
                )
                throw new Error("submit failed");
            })
            .then(
                response => {
                    // at this point we have successfully submitted the entry,
                    // mow we just need to submit any attachments.
                    const entryId = response.entry.id;                
                    Promise.all(this.submitAttachments(response.entry.id))
                           .then(response => {
                               // signal other parts of the app that the logbook needs refreshing
                               this.props.eventbus.publish("logbook.reload",
                                                           this.state.logbook.id);                
                               // send the browser to view the new entry
                               history.push(`/logbooks/${this.state.logbook.id}/entries/${entryId}`);
                           });
                },
                error => {
                    console.log(error);
                }
            );
    }

    renderInner (history) {
        
        if (!this.state.logbook)
            return <div>Loading...</div>;

        // Using a table here, because TinyMCE sometimes does not play well with
        // flexbox, causing height issues... hopefully this will be more robust.
        
        return (
            <div id="entryeditor">

                <Prompt message={this.getPromptMessage.bind(this)}/>

                <table>
                    <tr>
                        <th className="title">
                            New entry in <span className="logbook">
                            <i className="fa fa-book"/> {this.state.logbook.name || "[unknown]"}</span>
                        </th>
                    </tr>
                    <tr>
                        <td>
                            { this.getTitleEditor(this.state.title) }
                        </td>
                    </tr>
                    <tr>
                        <td>
                            { this.getAuthorsEditor(this.state.authors) }
                        </td>
                    </tr>
                    <tr>
                        <td className="attributes">
                            { this.getAttributesEditors(this.getAttributes()) }
                        </td>
                    </tr>
                    
                    <tr>
                        <td className="content">
                            { this.getContentHTMLEditor(this.state.content ||
                                                        this.state.logbook.template) }
                        </td>
                    </tr>
                    <tr>
                        <td>
                            { this.getAttachments(this.state.attachments) }
                        </td>
                    </tr>
                    <tr>
                        <td>{this.getError()}</td>
                    </tr>                    
                    <tr>
                        <td>
                            { this.getPrioritySelector() }
                            <div className="commands">
                                { this.getSubmitButton(history) }
                                { this.getCancelButton() }
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
        );        
    }
}



class EntryEditorFollowup extends EntryEditorBase {

    /* editor for creating a followup to an existing entry */

    componentWillMount () {
        this.fetchEntry(this.props.match.params.logbookId,
                        this.props.match.params.entryId);
        this.fetchLogbook(this.props.match.params.logbookId);        
    }

    hasEdits () {
        return (!this.submitted &&
                (this.state.title ||
                 this.state.content ||
                 this.state.authors.length > 0 ||
                 Object.keys(this.state.attributes).length > 0));
    }
    
    onSubmit({history}) {
        this.submitted = true;
        const attributes = {};
        // we want to default to the attributes of the original entry, but
        // apply any changes on top.
        this.state.logbook.attributes.forEach(
            attr => attributes[attr.name] = this.state.attributes.hasOwnProperty(attr.name)?
                                            this.state.attributes[attr.name] :
                                            this.state.entry.attributes[attr.name]
        );
        fetch(
            `/api/logbooks/${this.state.logbook.id}/entries/${this.state.entry.id}/`, {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: this.state.title,
                    authors: this.state.authors,
                    content: this.state.content,
                    content_type: this.state.content_type,
                    attributes: attributes,
                    archived: this.state.archived,
                    priority: this.state.priority,
                    metadata: this.state.metadata
                })
            })
            .then(response => {
                if (response.ok) {
                    return response.json()
                }
                response.json().then(
                    error => {this.setState({error: error})},
                    error => {this.setState({error: {message: response.statusText,
                                                     code: response.status}})}
                )
                throw new Error("submit failed");
            })
            .then(
                response => {
                    const entryId = response.entry.id;                
                    Promise.all(this.submitAttachments(response.entry.id))
                           .then(response => {
                               // signal other parts of the app that the logbook needs refreshing
                               this.props.eventbus.publish("logbook.reload",
                                                           this.state.logbook.id);                
                               // send the browser to view the new entry
                               history.push(`/logbooks/${this.state.logbook.id}/entries/${entryId}`);
                           });
                },
                error => {
                    console.log(error);
                }
            );
        
    }
    
    renderInner (history) {
        
        if (!this.state.logbook || !this.state.entry)
            return <div>Loading...</div>;

        return (
            <div id="entryeditor">

                <Prompt message={this.getPromptMessage.bind(this)}/>

                <table>
                    <tr>
                        <th className="title">
                            Followup to { this.state.entry.title } in <span className="logbook"> <i className="fa fa-book"/> {this.state.logbook.name || "ehe"}</span>
                        </th>
                    </tr>
                    <tr className="entry">
                        <td className="entry">
                            <div className="entry">
                                <InnerEntry hideLink={true} hideEditLink={true} {...this.state.entry}/>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            { this.getAuthorsEditor(this.state.authors) }
                        </td>
                    </tr>
                    <tr className="attributes">
                        <td>
                            { this.getAttributesEditors(this.getAttributes()) }
                        </td>
                    </tr>
                    
                    <tr>
                        <td className="content">
                            { this.getContentHTMLEditor(this.state.content ||
                                                        this.state.logbook.template) }
                        </td>
                    </tr>
                    <tr>
                        <td>
                            { this.getAttachments(this.state.attachments) }
                        </td>
                    </tr>
                    <tr>
                        <td>{this.getError()}</td>
                    </tr>                                        
                    <tr>
                        <td>
                            <div className="commands">
                                { this.getSubmitButton(history) }
                                { this.getCancelButton() }
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
        );        

                
    }
}



class EntryEditorEdit extends EntryEditorBase {

    /* editor for changing an existing entry */

    constructor (props) {
        super(props);
        this.state.lockedBySomeoneElse = false;
    }
    
    lockEntry (logbookId, entryId) {
        fetch(`/api/logbooks/${logbookId}/entries/${entryId}/lock`,
              {method: "POST"})
            .then(response => {
                console.log(response);
                return response.json()
            })
            .then(response => {
                console.log(response);
                if (response.status === 409) {
                    // The entry is locked by someone else!
                    this.setState({lockedBySomeoneElse: true});                                        
                } else {
                    // Either we got a new lock, or we already had it
                    // and we just get the same lock.
                    this.setState({lock: response.lock})
                }
            });
    }

    stealEntryLock (logbookId, entryId) {
        fetch(`/api/logbooks/${logbookId}/entries/${entryId}/lock?steal=true`,
              {method: "POST"})
            .then(response => {
                console.log(response);
                return response.json()
            })
            .then(response => {
                console.log(response);
                this.setState({lockedBySomeoneElse: false,
                               lock: response.lock})
            });
    }

    componentWillMount () {
        this.fetchLogbook(this.props.match.params.logbookId);
        this.fetchEntry(this.props.match.params.logbookId,
                        this.props.match.params.entryId, true);
        this.lockEntry(this.props.match.params.logbookId,
                       this.props.match.params.entryId);
    }

    onStealLock() {
        this.stealEntryLock(this.props.match.params.logbookId,
                            this.props.match.params.entryId);
    }
    
    onSubmit({history}) {
        this.submitted = true;
        // we're creating a new entry
        fetch(
            `/api/logbooks/${this.state.logbook.id}/entries/${this.state.entry.id}/`, {
                method: "PUT",
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: this.state.title,
                    authors: this.state.authors,
                    content: this.state.content,
                    content_type: this.state.content_type,
                    attributes: this.state.attributes,
                    metadata: this.state.metadata,
                    follows_id: this.state.follows,
                    archived: this.state.archived,
                    revision_n: this.state.entry.revision_n,  // must be included for edits!
                    priority: this.state.priority
                })
            })
            .then(response => {
                if (response.ok) {
                    return response.json()
                }
                response.json().then(
                    error => {this.setState({error: error})},
                    error => {this.setState({error: {message: response.statusText,
                                                     code: response.status}})}
                )
                throw new Error("submit failed");
            })
            .then(
                response => {
                    const entryId = response.entry.id;                
                    Promise.all(this.submitAttachments(response.entry.id))
                           .then(response => {
                               // signal other parts of the app that the logbook needs refreshing
                               this.props.eventbus.publish("logbook.reload",
                                                           this.state.logbook.id);                
                               // send the browser to view the new entry
                               history.push(`/logbooks/${this.state.logbook.id}/entries/${entryId}`);
                           });
                },
                error => {
                    console.log(error);
                }
            );
    }

    getLockInfo () {
        if (this.state.lockedBySomeoneElse) {
            return (
                <span className="locked-by-someone-else"
                      title={`This entry is locked by ${this.state.lock.owned_by_ip} since ${this.state.lock.created_at} in order to prevent edit conflicts.`}>
                    Locked by {this.state.lock.owned_by_ip}!
                </span>
            );
        } else {
            return null;
        }
    }

    getSubmitButton (history) {
        if (this.state.lockedBySomeoneElse) {
            /* 
               Since it's not allowed to submit an entry that is locked
               by someone else, we don't show the Submit button here.
               It's possible however to explicitly "steal" the lock,
               e.g. if the user knows that the lock is no longer 
               relevant.
            */
            return (
                <span>                    
                    <button className="steal-lock"
                            title="If you are certain that the lock is not relevant (e.g. the owner is not going to submit any changes) you can explicitly 'steal' the lock, allowing you to submit instead."
                            onClick={this.onStealLock.bind(this)}>
                        Steal lock
                    </button>
                </span>
            );
        } else {
            return (
                <button className="submit"
                        title="Upload the entry"
                        onClick={this.onSubmit.bind(this, history)}>
                    Submit
                </button>
            );
        }
    }

    getTitle () {
        // return a reasonable title
        // TODO: if editing a followup, ther's usually no title. It would be nice to be able
        // to display the title of the original entry instead of only the ID...
        if (this.state.follows !== null) {
            return <div>Editing followup to [{this.state.follows}] in <span className="logbook">
                <i className="fa fa-book"/> {this.state.logbook.name || "[unknown]"}</span></div>
        } else {
            return <div>Editing '{ this.state.title }' in <span className="logbook">
                <i className="fa fa-book"/> {this.state.logbook.name || "[unknown]"}</span></div>
        }
    }
    
    renderInner (history) {
        
        if (!(this.state.logbook && this.state.entry))
            return <div>Loading...</div>;

        return (
            <div id="entryeditor">

                <Prompt message={this.getPromptMessage.bind(this)}/>

                <table>
                    <tr>
                        <th className="title">
                            { this.getTitle() }
                        </th>
                    </tr>
                    <tr>
                        <td>
                            {
                                this.state.follows?
                                null :
                                this.getTitleEditor(this.state.title)
                            }
                        </td>
                    </tr>
                    <tr>
                        <td>
                            { this.getAuthorsEditor(this.state.authors) }
                        </td>
                    </tr>
                    <tr className="attributes">
                        <td>
                            { this.getAttributesEditors(this.getAttributes()) }
                        </td>
                    </tr>
                    
                    <tr>
                        <td className="content">
                            { this.getContentHTMLEditor(this.state.content ||
                                                        this.state.logbook.template) }
                        </td>
                    </tr>
                    <tr>
                        <td>
                            { this.getAttachments(this.state.attachments) }
                        </td>
                    </tr>
                    <tr>
                        <td>{this.getError()}</td>
                    </tr>                    
                    <tr>
                        <td>
                            { this.getPrioritySelector() }
                            { this.getLockInfo() }
                            <div className="commands">
                                { this.getSubmitButton(history) }
                                { this.getCancelButton() }
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
        );        
    }
}


class EntryEditor extends React.Component {

    /* just a dummy component that routes to the correct editor */
    
    render () {
        return (
            <Switch>
                <Route path="/logbooks/:logbookId/entries/new" 
                       component={withProps(EntryEditorNew, this.props)}/>
                <Route path="/logbooks/:logbookId/entries/:entryId/new" 
                       component={withProps(EntryEditorFollowup, this.props)}/>
                <Route path="/logbooks/:logbookId/entries/:entryId/edit" 
                       component={withProps(EntryEditorEdit, this.props)}/>            
            </Switch>
        );
    }   
}


export default EntryEditor;
    
