import React from 'react';
import { findDOMNode } from 'react-dom';
import update from 'immutability-helper';
import TinyMCEInput from './TinyMCEInput.js';

import {Link, Route, Prompt} from 'react-router-dom';
import TINYMCE_CONFIG from './tinymceconfig.js';
import './logbookeditor.css';


// Editor for a single logbook attribute
class LogbookAttributeEditor extends React.PureComponent {

    constructor (props) {
        super(props);
        this.state = {
            name: props.name,
            type: props.type,
            options: props.options,
            required: props.required
        }
    }
    
    onChangeName (event) {
        this.setState({name: event.target.value});
    }

    onChangeType (event) {
        this.setState({type: event.target.value});
    }

    onChangeOptions (event) {
        this.setState({options: event.target.value.split("\n")});
    }

    onChangeRequired (event) {
        this.setState({required: event.target.checked});
    }

    onBlur () {
        this.props.onChange(this.props.index, this.state);
    }
    
    render () {
        return (
            <div className="attribute">
                <label>
                    <input type="text" ref="name"
                           value={this.state.name}
                           onChange={this.onChangeName.bind(this)}
                           onBlur={this.onBlur.bind(this)}/>
                </label>
                <label>
                    Type:
                    <select name="type" ref="type" value={this.state.type}
                            onChange={this.onChangeType.bind(this)}
                            onBlur={this.onBlur.bind(this)}>
                        <option value="text">Text</option>
                        <option value="number">Number</option>
                        <option value="boolean">Boolean</option>
                        <option value="option">Option</option>
                        <option value="multioption">Multioption</option>
                    </select>
                </label>
                <label>
                    <input type="checkbox" ref="required"
                           checked={this.state.required}
                           onChange={this.onChangeRequired.bind(this)}
                           onBlur={this.onBlur.bind(this)}/>
                    Required                        
                </label>
                <label style={
                    {display: (this.props.type == "option" ||
                               this.props.type == "multioption")?
                              "inline-block" : "none"}}>
                    Options:
                    <textarea rows="3" ref="options"
                              value={(this.state.options || []).join("\n")}
                              onChange={this.onChangeOptions.bind(this)}
                              onBlur={this.onBlur.bind(this)}/>
                </label>
            </div>
        );
    }    
}


// Edit a logbook 
class LogbookEditor extends React.Component {

    constructor (props) {
        super(props);
        this.state = {
            name: "",
            description: "",
            metadata: {},
            attributes: [],
            parent: {}
        }
    }

    fetchLogbook () {
        fetch(`/api/logbooks/${this.props.match.params.logbookId || 0}/`,
              {headers: {"Accept": "application/json"}})
            .then(response => response.json())
            .then(json => {this.setState({logbook: json.logbook,
                                          ...json.logbook})});
    }

    componentWillMount() {
        if (this.props.match.params.logbookId > 0) {
            console.log("fetch", this.props.match.params.logbookId);
            this.fetchLogbook();
        }
    }

    changeName(event) {
        this.setState({name: event.target.value});
    }

    changeDescription (event) {
        this.setState({description: event.target.value});
    }
    
    findAttribute(name) {
        const attr = this.state.attributes.find(attr => attr.name == name);
        return this.state.attributes.indexOf(attr);            
    }
    
    changeAttribute(index, attr) {
        this.setState(update(this.state, {attributes: {[index]: {$set: attr}}}));
    }

    removeAttribute(index, event) {
        event.preventDefault();        
        this.setState(update(this.state, {attributes: {$splice: [[index, 1]]}}));
    }

    insertAttribute(index, event) {
        event.preventDefault();
        const newAttribute = {type: "text",
                              name: "New attribute",
                              options: [],
                              required: false}
        this.setState(
            update(this.state,
                   {attributes: {$splice: [[index, 0, newAttribute]]}}));
    }

    moveAttribute(index, delta, event) {
        event.preventDefault();        
        const newIndex = index + delta;
        if (newIndex < 0 || newIndex > this.state.attributes.length -1)
            return;
        const attr = this.state.attributes[index];
        var state = update(this.state, {attributes: {$splice: [[index, 1]]}});
        state = update(state, {attributes: {$splice: [[newIndex, 0, attr]]}});
        this.setState(state);
    }

    onTemplateChange(value) {
        this.setState({template: value});
    }

    hasEdits () {
        const original = this.state.logbook || {};
        return (!this.submitted &&
                (this.state.name !== original.name ||
                 this.state.description !== original.description ||
                 this.state.template !== original.template ||
                 this.state.attributes !== original.attributes));
    }

    getPromptMessage () {
        if (this.hasEdits())
            return "Looks like you have made some edits. If you leave, you will lose those...";
    }
    
    onSubmit (history) {
        this.submitted = true;
        if (this.props.match.params.logbookId &&
            this.props.match.params.command === "edit") {
            // editing an existing logbook
            fetch(
                `/api/logbooks/${this.state.id}/`, {
                    method: "PUT",
                    headers: {
                        'Content-Type': 'application/json'
                    },                                            
                    body: JSON.stringify({
                        id: this.state.id,
                        parent_id: this.state.parent? this.state.parent.id : null,                        
                        name: this.state.name,
                        description: this.state.description,
                        attributes: this.state.attributes,
                        template: this.state.newTemplate || this.state.template,
                        template_content_type: "text/html",
                    })
                })
                .then(result => result.json())
                .then(result => {
                    history.push({
                        pathname: `/logbooks/${this.state.id}`,
                    });
                    this.props.eventbus.publish("logbook.reload", this.state.id);
                });
        } else {
            // creating a new logbook
            // either as a new toplevel, or as a child of the given logbook
            const url = this.props.match.params.logbookId?
                        `/api/logbooks/${this.props.match.params.logbookId}/` :
                        "/api/logbooks/";
            fetch(
                url, {
                    method: "POST",
                    headers: {
                        'Content-Type': 'application/json'
                    },                    
                    body: JSON.stringify({
                        parent_id: this.state.parent? this.state.parent.id : null,
                        name: this.state.name,
                        description: this.state.newDescription || this.state.description,
                        attributes: this.state.attributes,
                        template: this.state.newTemplate || this.state.template,
                        template_content_type: "text/html",
                    })
                })
                .then(result => result.json())
                .then(result => {
                    this.props.eventbus.publish("logbook.reload", this.state.id);
                    history.push({pathname: `/logbooks/${result.id}`});
                });
        }
    }
    
    innerRender ({history}) {
        console.log("eroadsom", this.state);        

        const attributes = this.state.attributes.map(
            (attr, i) => (
                <fieldset key={i}>
                    <legend>{i}
                        <button onClick={this.removeAttribute.bind(this, i)}>
                            <i className="fa fa-trash"/>
                        </button>
                        <button onClick={this.insertAttribute.bind(this, i)}>
                            <i className="fa fa-plus"/>
                        </button>
                        <button onClick={this.moveAttribute.bind(this, i, -1)}>
                            <i className="fa fa-arrow-up"/>
                        </button>
                        <button onClick={this.moveAttribute.bind(this, i, 1)}>
                            <i className="fa fa-arrow-down"/>
                        </button>
                    </legend>
                    <LogbookAttributeEditor
                        key={attr.name}
                        index={i}
                        type={attr.type}
                        name={attr.name}
                        options={attr.options}
                        required={attr.required}
                        onChange={this.changeAttribute.bind(this)}/>
                </fieldset>
            )
        );
        
        return (
            <div id="logbookeditor">
                
                <Prompt message={this.getPromptMessage.bind(this)}/>
                
                <header>
                    {this.props.match.params.command == "edit"?
                     `Editing logbook ${this.state.parent && this.state.parent.name || ""}/${this.state.name}`:
                     `New logbook in "${this.state.logbook? this.state.logbook.name : ''}"`}

                </header>
                
                <form>
                    <fieldset>
                        <legend>Name</legend>
                        <input type="text" name="name"
                               value={this.state.name}
                               onChange={this.changeName.bind(this)}/>
                    </fieldset>
                    <fieldset className="description">
                        <legend>Description</legend>
                        <textarea name="description" rows={5}
                                  value={this.state.description}
                                  onChange={this.changeDescription.bind(this)}/>
                    </fieldset>
                    <fieldset className="template">
                        <legend>Template</legend>
                        <TinyMCEInput
                            value={this.state.template || ""}
                            tinymceConfig={ TINYMCE_CONFIG }
                            onChange={this.onTemplateChange.bind(this)}/>
                    </fieldset>
                    <fieldset className="attributes">
                        <legend>Attributes</legend>
                        <div className="attributes">
                            {attributes}
                        </div>
                        <button onClick={this.insertAttribute.bind(this, this.state.attributes.length)}>New</button>
                    </fieldset>
                </form>
                
                <footer>
                    <button onClick={this.onSubmit.bind(this, history)}>
                        Submit
                    </button>
                </footer>
                
            </div>
        );
    }

    render () {
        return <Route render={this.innerRender.bind(this)}/>
    }
    
}


export default LogbookEditor;
