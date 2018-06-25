import React from "react";
import { findDOMNode } from "react-dom";
import { formatDateTimeString } from "./util.js";

const ICON_CLASS_MAP = {
    "application/vnd.ms-excel": "fa fa-file-excel-o",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        "fa fa-file-excel-o",
    "application/pdf": "fa fa fa-file-pdf-o",
    "text/plain": "fa fa-file-text-o",
    "text/csv": "fa fa-file-text-o",
    "application/zip": "fa fa-file-archive-o"
    // TODO: detect more file types
};

export const RemoteAttachmentPreview = ({ attachment }) => {
    // display an appropriate icon for the given attachment
    if (!attachment.content_type) {
        return <i className="fa fa-file-o fa-2x" />;
    }
    const contentType = attachment.content_type.split(";")[0].toLowerCase();
    if (ICON_CLASS_MAP[contentType]) {
        return (
            <i className={ICON_CLASS_MAP[attachment.content_type] + " fa-2x"} />
        );
    }
    if (attachment.metadata && attachment.metadata.thumbnail_size) {
        return (
            <img
                src={attachment.thumbnail_link}
                width={attachment.metadata.thumbnail_size.width}
                height={attachment.metadata.thumbnail_size.height}
                alt={attachment.filename}
            />
        );
    }
    return <i className="fa fa-file-o fa-2x" />;
};

export class LocalAttachmentPreview extends React.Component {
    componentDidMount() {
        const image = findDOMNode(this.refs.image);
        if (image) {
            image.src = this.props.attachment.preview;
        }
    }

    render() {
        if (this.props.attachment.type.split("/")[0] === "image") {
            return <img ref="image" width="100" alt="" />;
        }
        const iconClass =
            ICON_CLASS_MAP[this.props.attachment.type] || "fa fa-file-o fa-2x";
        return <i className={iconClass} />;
    }
}

export const AttachmentPreviewIcon = ({ attachment }) =>
    attachment.link ? (
        <RemoteAttachmentPreview attachment={attachment} />
    ) : (
        <LocalAttachmentPreview attachment={attachment} />
    );

export const AttachmentPreview = ({ attachment }) => (
    <tr>
        <td>
            <div className="preview">
                <a href={attachment.link}>
                    <AttachmentPreviewIcon attachment={attachment} />
                </a>
            </div>
        </td>
        <td>
            <div className="filename">
                <a href={attachment.link}>{attachment.filename}</a>
            </div>
            <div className="timestamp">
                {attachment.timestamp
                    ? formatDateTimeString(attachment.timestamp)
                    : ""}
            </div>
            <div className="size">
                {attachment.metadata && attachment.metadata.size
                    ? `${attachment.metadata.size.width}⨯${attachment.metadata
                          .size.height}`
                    : ""}
            </div>
        </td>
    </tr>
);




export const EntryAttachments = ({ attachments, onRemove }) => (
    <div className="attachments">
        <table>
            {attachments.map((att, i) => (
                <tbody className="attachment" key={i} title={att.filename}>
                    {onRemove ? 
                        <div className="attachment-delete"><button
                        className="delete"
                        title="Delete the attachment"
                        onClick={onRemove.bind(this, i)}
                    > x </button> </div>: null}
                    <AttachmentPreview attachment={att} />
                </tbody>
            ))}
        </table>
    </div>
);

export default EntryAttachments;
