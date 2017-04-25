import React from 'react';
import { findDOMNode } from 'react-dom';
import update from 'immutability-helper';

import {Link, Route} from 'react-router-dom';
import style from './logbookeditor.css';


class LogbookAttribute extends React.PureComponent {

    onChange () {
        this.props.onChange(this.props.index, {
            name: findDOMNode(this.refs.name).value,
            type: findDOMNode(this.refs.type).value,
            options: findDOMNode(this.refs.options).value.split("\n"),
            required: findDOMNode(this.refs.required).checked
        });
    }
    
    render () {
        return (
            <div className="attribute">
                <label>
                    <input type="text" ref="name"
                           value={this.props.name}
                           onChange={this.onChange.bind(this)}/>
                </label>
                <label>
                    Type:
                    <select name="type" ref="type" value={this.props.type}
                            onChange={this.onChange.bind(this)}>
                        <option value="text">Text</option>
                        <option value="number">Number</option>
                        <option value="boolean">Boolean</option>                    
                        <option value="option">Option</option>
                        <option value="multioption">Multioption</option>
                    </select>
                </label>
                <label>
                    <input type="checkbox" ref="required"
                           checked={this.props.required}
                           onChange={this.onChange.bind(this)}/>
                    Required                        
                </label>
                <label style={
                    {display: (this.props.type == "option" ||
                               this.props.type == "multioption")?
                              "inline-block" : "none"}}>
                    Options:
                    <textarea rows="3" ref="options"
                              value={this.props.options.join("\n")}
                              onChange={this.onChange.bind(this)}/>
                </label>
            </div>
        );
    }
    
}


class LogbookEditor extends React.Component {

    constructor (props) {
        super(props);
        this.state = {
            name: "",
            description: "",
            attributes: [],
            parent: {}
        }
    }

    fetchLogbook () {
        fetch(`/logbooks/${this.props.match.params.logbookId || 0}`,
              {headers: {"Accept": "application/json"}})
               .then(response => response.json())
               .then(json => {this.setState(json)});
    }

    componentWillMount() {
        this.fetchLogbook();
    }

    changeName(event) {
        this.setState({newName: event.target.value});
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

    onSubmit (history) {
        if (this.state.id) {
            fetch(
                `/logbooks/${this.state.id}`, {
                    method: "PUT",
                    headers: {
                        'Content-Type': 'application/json'
                    },                                            
                    body: JSON.stringify({
                        id: this.state.id,
                        name: this.state.name,
                        description: this.state.description,
                        attributes: this.state.attributes
                    })
                })
                .then(result => result.json())
                .then(result => history.push({
                    pathname: `/logbooks/${this.state.id}`,
                    state: {reloadLogbook: true}
                }));
        } else {
            fetch(
                `/logbooks/`, {
                    method: "POST",
                    headers: {
                        'Content-Type': 'application/json'
                    },                    
                    body: JSON.stringify({
                        name: this.state.name,
                        description: this.state.description,
                        attributes: this.state.attributes
                    })
                })
                .then(result => result.json())
                .then(result => history.push({
                    pathname: `/logbooks/${result.logbook}`
                }));
        }
    }
    
    innerRender ({history}) {

        const attributes = this.state.attributes.map(
            (attr, i) => (
                <fieldset key={i}>
                    <legend>{i}
                        <button onClick={this.removeAttribute.bind(this, i)}>Delete</button>
                        <button onClick={this.insertAttribute.bind(this, i)}>Insert</button>
                        <button onClick={this.moveAttribute.bind(this, i, -1)}>Up</button>
                        <button onClick={this.moveAttribute.bind(this, i, 1)}>Down</button>
                    </legend>
                    <LogbookAttribute
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
                <header>
                    {this.props.match.url.substr(-4) == "edit"?
                     `Editing logbook ${this.state.parent.name || ""}/${this.state.name}`:
                     `New logbook in "${this.state.parent.name}"`}
                </header>
                <form>
                    <fieldset>
                        <legend>Name</legend>
                        <input type="text" name="name"
                               value={this.state.newName || this.state.name}
                               onChange={this.changeName.bind(this)}/>
                    </fieldset>
                    <fieldset className="description">
                        <legend>Description</legend>
                        <textarea name="description" rows={5}
                                  value={this.state.description}
                                  onChange={this.changeDescription.bind(this)}/>
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
                    <button onClick={this.onSubmit.bind(this, history)}>Submit</button>
                </footer>
            </div>
        );
    }

    render () {
        return <Route render={this.innerRender.bind(this)}/>
    }
    
}


export default LogbookEditor;
