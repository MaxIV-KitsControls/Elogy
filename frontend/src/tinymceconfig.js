// configuration for the editor
const TINYMCE_CONFIG = {
    plugins: "link image textcolor paste table lists advlist code insertdatetime",
    toolbar: (
        "undo redo | removeformat | styleselect |"
        + " bold italic forecolor backcolor |"
        + " bullist numlist outdent indent | link image table insertdatetime | code"
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
    theme: "modern",
    branding: false,
    insertdatetime_formats: ["%A %Y-%m-%d %H:%M:%S"],
};

export default TINYMCE_CONFIG;
