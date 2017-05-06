import React from "react";


const ICON_CLASS_MAP = {
    "application/vnd.ms-excel": "fa fa-file-excel-o",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "fa fa-file-excel-o",
    'application/pdf': "fa fa fa-file-pdf-o",
    "text/plain": "fa fa-file-text-o",
    "text/csv": "fa fa-file-text-o",
    'application/zip': "fa fa-file-archive-o"
    // TODO: detect more file types
}


export const AttachmentPreview = ({attachment}) => {
    // display an appropriate icon for the given attachment
    if (!attachment.content_type) {
        return <i className="fa fa-file-o fa-2x"/>
    }
    const contentType = attachment.content_type.split(";")[0].toLowerCase();
    if (ICON_CLASS_MAP[contentType]) {
        return <i className={ICON_CLASS_MAP[attachment.content_type] + " fa-2x"}/>;
    }
    if (attachment.metadata && attachment.metadata.thumbnail_size) {
        return <img src={`/attachments/${attachment.path}.thumbnail`}
                    width={attachment.metadata.thumbnail_size.width}
                    height={attachment.metadata.thumbnail_size.height}/>
    }
    return <i className="fa fa-file-o fa-2x"/>;
};


export const EntryAttachments = ({attachments}) => (
    <div className="attachments">
    {
        attachments
            .map((att, i) => (
                <span className="attachment" key={i} title={att.filename}>
                    <a href={`/attachments/${att.path}`}>
                        <AttachmentPreview attachment={att}/>
                    </a>
                </span>
            ))
    }
    </div>
)


export default EntryAttachments;
