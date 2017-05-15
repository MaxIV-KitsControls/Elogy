import React from "react";


const EntryAttribute = ({config, value}) => (
    <span className="attribute">
        <span className="name">{config.name}</span>
        <span className="value">
            {
                // TODO: Let's say an attribute is reconfigured in the logbook
                // from "option" to "multioption". Should the backend always
                // convert the value to an array in this case? What about the
                // opposite case?
                config.type == "multioption"?
                value.map(v => <span className="option">{v}</span>)
                : value
            }
        </span>
    </span>
);


const EntryAttributes = ({attributes, logbook}) => (
    <div className="attributes">
    {
        logbook.attributes
               .filter(attr => attributes[attr.name])
               .map((attr, i) => <EntryAttribute key={i} config={attr} value={attributes[attr.name]}/>)
    }
    </div>
);


export default EntryAttributes;
