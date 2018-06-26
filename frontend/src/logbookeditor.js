import React from "react";
import { Route, Prompt, Switch } from "react-router-dom";
import update from "immutability-helper";
import TinyMCEInput from "./TinyMCEInput.js";

import TINYMCE_CONFIG from "./tinymceconfig.js";
import { withProps } from "./util.js";
import { LogbookSelector } from "./logbookselector.js";
import "./logbookeditor.css";

// Editor for a single logbook attribute
class LogbookAttributeEditor extends React.PureComponent {
    constructor(props) {
        super(props);
        this.state = {
            name: props.name,
            type: props.type || "text",
            options: props.options,
            required: props.required
        };
    }

    onChangeName(event) {
        this.setState({ name: event.target.value });
    }

    onChangeType(event) {
        this.setState({ type: event.target.value });
    }

    onChangeOptions(event) {
        this.setState({ options: event.target.value.split("\n") });
    }

    onChangeRequired(event) {
        this.setState({ required: event.target.checked });
    }

    onBlur() {
        this.props.onChange(this.props.index, this.state);
    }

    render() {
        return (
            <div className="attribute">
                <label>
                    <input
                        type="text"
                        ref="name"
                        value={this.state.name}
                        onChange={this.onChangeName.bind(this)}
                        onBlur={this.onBlur.bind(this)}
                    />
                </label>
                <label>
                    Type:
                    <select
                        name="type"
                        ref="type"
                        value={this.state.type}
                        onChange={this.onChangeType.bind(this)}
                        onBlur={this.onBlur.bind(this)}
                    >
                        <option value="text">Text</option>
                        <option value="number">Number</option>
                        <option value="boolean">Boolean</option>
                        <option value="option">Option</option>
                        <option value="multioption">Multioption</option>
                    </select>
                </label>
                <label>
                    <input
                        type="checkbox"
                        ref="required"
                        checked={this.state.required}
                        onChange={this.onChangeRequired.bind(this)}
                        onBlur={this.onBlur.bind(this)}
                    />
                    Required
                </label>
                <label
                    style={{
                        display:
                            this.state.type === "option" ||
                            this.state.type === "multioption"
                                ? "inline-block"
                                : "none"
                    }}
                >
                    Options:
                    <textarea
                        rows="3"
                        ref="options"
                        title="Choices available for the attribute (one per line)"
                        value={(this.state.options || []).join("\n")}
                        onChange={this.onChangeOptions.bind(this)}
                        onBlur={this.onBlur.bind(this)}
                    />
                </label>
            </div>
        );
    }
}

// Edit a logbook
class LogbookEditorBase extends React.Component {
    /* Base class for logbook editors
       The idea is to make different subclasses depending on whether
       we're creating a new lognbook or editing an existing one. This
       cuts down on the amount of conditional logic.*/

    componentWillMount() {
        if (this.props.match.params.logbookId > 0) {
            this.fetch();
        }
    }

    changeName(event) {
        this.setState({ name: event.target.value });
    }

    changeDescription(event) {
        this.setState({ description: event.target.value });
    }

    getAttributes(logbook) {
        return this.state.attributes.map((attr, i) => (
            <fieldset key={i}>
                <legend>
                    {i}
                    <button onClick={this.removeAttribute.bind(this, i)}>
                        <i className="fa fa-trash" />
                    </button>
                    <button onClick={this.insertAttribute.bind(this, i)}>
                        <i className="fa fa-plus" />
                    </button>
                    <button onClick={this.moveAttribute.bind(this, i, -1)}>
                        <i className="fa fa-arrow-up" />
                    </button>
                    <button onClick={this.moveAttribute.bind(this, i, 1)}>
                        <i className="fa fa-arrow-down" />
                    </button>
                </legend>
                <LogbookAttributeEditor
                    key={attr.name}
                    index={i}
                    type={attr.type}
                    name={attr.name}
                    options={attr.options}
                    required={attr.required}
                    onChange={this.changeAttribute.bind(this)}
                />
            </fieldset>
        ));
    }

    findAttribute(name) {
        const attr = this.state.attributes.find(attr => attr.name === name);
        return this.state.attributes.indexOf(attr);
    }

    changeAttribute(index, attr) {
        this.setState(
            update(this.state, { attributes: { [index]: { $set: attr } } })
        );
    }

    removeAttribute(index, event) {
        event.preventDefault();
        this.setState(
            update(this.state, { attributes: { $splice: [[index, 1]] } })
        );
    }

    insertAttribute(index, event) {
        event.preventDefault();
        const newAttribute = {
            type: "text",
            name: "New attribute",
            options: [],
            required: false
        };
        this.setState(
            update(this.state, {
                attributes: { $splice: [[index, 0, newAttribute]] }
            })
        );
    }

    moveAttribute(index, delta, event) {
        event.preventDefault();
        const newIndex = index + delta;
        if (newIndex < 0 || newIndex > this.state.attributes.length - 1) return;
        const attr = this.state.attributes[index];
        var state = update(this.state, {
            attributes: { $splice: [[index, 1]] }
        });
        state = update(state, {
            attributes: { $splice: [[newIndex, 0, attr]] }
        });
        this.setState(state);
    }

    onTemplateChange(value) {
        this.setState({ template: value });
    }

    hasEdits() {
        const original = this.state.logbook || {};
        return (
            !this.submitted &&
            (this.state.name !== original.name ||
                this.state.description !== original.description ||
                this.state.template !== original.template ||
                this.state.attributes !== original.attributes)
        );
    }

    getPromptMessage() {
        if (this.hasEdits())
            return "Looks like you are making edits to a logbook! If you leave, you will lose those.";
    }

    getErrors() {
        if (this.state.error) {
            return (
                <div className="error" title="Error received from the server">
                    {JSON.stringify(this.state.error.messages)}
                </div>
            );
        }
    }

    render() {
        return <Route render={this.innerRender.bind(this)} />;
    }
}

class LogbookEditorNew extends LogbookEditorBase {
    constructor(props) {
        super(props);
        this.state = {
            name: "",
            description: "",
            metadata: {},
            attributes: [],
            parent: {},
            error: null
        };
    }

    fetch() {
        fetch(`/api/logbooks/${this.props.match.params.logbookId || 0}/`, {
            headers: { Accept: "application/json" }
        })
            .then(response => response.json())
            .then(json =>
                this.setState({
                    parent: json.logbook,
                    attributes: json.logbook.attributes
                })
            );
    }

    onSubmit(history) {
        this.submitted = true;
        // creating a new logbook
        // either as a new toplevel, or as a child of the given logbook
        const url = this.props.match.params.logbookId
            ? `/api/logbooks/${this.props.match.params.logbookId}/`
            : "/api/logbooks/";
        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                parent_id: this.state.parent ? this.state.parent.id : null,
                name: this.state.name,
                description:
                    this.state.newDescription || this.state.description,
                attributes: this.state.attributes,
                template: this.state.newTemplate || this.state.template,
                template_content_type: "text/html"
            })
        })
            .then(response => {
                if (response.ok) {
                    return response.json();
                }
                response.json().then(
                    error => {
                        this.setState({ error: error });
                    },
                    error => {
                        this.setState({
                            error: {
                                message: response.statusText,
                                code: response.status
                            }
                        });
                    }
                );
                throw new Error("submit failed");
            })
            .then(
                result => {
                    this.props.eventbus.publish(
                        "logbook.reload",
                        this.state.id
                    );
                    history.push({
                        pathname: `/logbooks/${result.logbook.id}`,
                        search: window.location.search
                    });
                },
                error => console.log(error)
            );
    }

    innerRender({ history }) {
        return (
            <div id="logbookeditor">
                <Prompt message={this.getPromptMessage.bind(this)} />

                <header>
                    {this.state.parent.id
                        ? `New logbook in "${this.state.parent.name}"`
                        : "New top level logbook"}
                </header>

                <form>
                    <fieldset>
                        <legend>Name</legend>
                        <input
                            type="text"
                            name="name"
                            value={this.state.name}
                            onChange={this.changeName.bind(this)}
                        />
                    </fieldset>
                    <fieldset className="description">
                        <legend>Description</legend>
                        <textarea
                            name="description"
                            rows={5}
                            value={this.state.description}
                            onChange={this.changeDescription.bind(this)}
                        />
                    </fieldset>
                    <fieldset className="template">
                        <legend title="This will be the default content of entries created in this logbook.">
                            Template
                        </legend>
                        <TinyMCEInput
                            value={this.state.template || ""}
                            tinymceConfig={TINYMCE_CONFIG}
                            onChange={this.onTemplateChange.bind(this)}
                        />
                    </fieldset>
                    <fieldset className="attributes">
                        <legend title="Name/value pairs that can be attached to entries in the logbook">
                            Attributes
                        </legend>
                        <div className="attributes">{this.getAttributes()}</div>
                        <button
                            onClick={this.insertAttribute.bind(
                                this,
                                this.state.attributes.length
                            )}
                        >
                            New
                        </button>
                    </fieldset>
                </form>

                {this.getErrors()}

                <footer>
                    <button onClick={this.onSubmit.bind(this, history)}>
                        Submit
                    </button>
                </footer>
            </div>
        );
    }
}

class LogbookEditorEdit extends LogbookEditorBase {
    constructor(props) {
        super(props);
        this.state = {
            name: "",
            description: "",
            metadata: {},
            attributes: [],
            logbook: {},
            archived: false,
            error: null
        };
    }

    fetch() {
        fetch(`/api/logbooks/${this.props.match.params.logbookId || 0}/`, {
            headers: { Accept: "application/json" }
        })
            .then(response => response.json())
            .then(json =>
                this.setState({
                    logbook: json.logbook,
                    ...json.logbook
                })
            );
    }

    onSubmit(history) {
        this.submitted = true;
        const parentId =
            this.state.parentId ||
            (this.state.parent ? this.state.parent.id : null);
        fetch(`/api/logbooks/${this.state.id}/`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                id: this.state.id,
                parent_id: parentId !== 0 ? parentId : null,
                name: this.state.name,
                description: this.state.description,
                attributes: this.state.attributes,
                archived: this.state.archived,
                template: this.state.newTemplate || this.state.template,
                template_content_type: "text/html"
            })
        })
            .then(response => {
                if (response.ok) {
                    return response.json();
                }
                response.json().then(
                    error => {
                        this.setState({ error: error });
                    },
                    error => {
                        this.setState({
                            error: {
                                message: response.statusText,
                                code: response.status
                            }
                        });
                    }
                );
                throw new Error("submit failed");
            })
            .then(
                result => {
                    history.push({
                        pathname: `/logbooks/${this.state.id}`,
                        search: window.location.search
                    });
                    this.props.eventbus.publish(
                        "logbook.reload",
                        this.state.id
                    );
                },
                error => console.log(error)
            );
    }

    onParentChange(parentId) {
        this.setState({ parentId: parentId });
    }

    onArchivedChange(event) {
        this.setState({ archived: event.target.checked });
    }

    innerRender({ history }) {
        const parentId =
            this.state.parentId ||
            (this.state.parent ? this.state.parent.id : 0);

        if (!this.state.id)
            return <div>Loading...</div>;

        return (
            <div id="logbookeditor">
                <Prompt message={this.getPromptMessage.bind(this)} />

                <header>
                    Editing logbook "{this.state.logbook.name}" in
                    <LogbookSelector
                        logbookId={parentId}
                        excludeId={this.state.id}
                        onLogbookChange={this.onParentChange.bind(this)}
                    />
                </header>

                <form>
                    <fieldset>
                        <legend>Name</legend>
                        <input
                            type="text"
                            name="name"
                            value={this.state.name}
                            onChange={this.changeName.bind(this)}
                        />
                    </fieldset>
                    <fieldset className="description">
                        <legend>Description</legend>
                        <textarea
                            name="description"
                            rows={5}
                            value={this.state.description}
                            onChange={this.changeDescription.bind(this)}
                        />
                    </fieldset>
                    <fieldset className="template">
                        <legend>Template</legend>
                        <TinyMCEInput
                            value={this.state.template || ""}
                            tinymceConfig={TINYMCE_CONFIG}
                            onChange={this.onTemplateChange.bind(this)}
                        />
                    </fieldset>
                    <fieldset className="attributes">
                        <legend>Attributes</legend>
                        <div className="attributes">{this.getAttributes()}</div>
                        <button
                            onClick={this.insertAttribute.bind(
                                this,
                                this.state.attributes.length
                            )}
                        >
                            New
                        </button>
                    </fieldset>
                </form>

                {this.getErrors()}

                <footer>
                    <label>
                        <input
                            type="checkbox"
                            checked={this.state.archived}
                            onChange={this.onArchivedChange.bind(this)}
                        />
                        Archived
                    </label>

                    <button onClick={this.onSubmit.bind(this, history)}>
                        Submit
                    </button>
                </footer>
            </div>
        );
    }
}

class LogbookEditor extends React.Component {
    /* just a dummy component that routes to the correct editor */

    render() {
        return (
            <Switch>
                <Route
                    path="/logbooks/new"
                    component={withProps(LogbookEditorNew, this.props)}
                />
                <Route
                    path="/logbooks/:logbookId/new"
                    component={withProps(LogbookEditorNew, this.props)}
                />
                <Route
                    path="/logbooks/:logbookId/edit"
                    component={withProps(LogbookEditorEdit, this.props)}
                />
            </Switch>
        );
    }
}

export default LogbookEditor;
