function generate_thumbnail(id){
$.ajax({
        type: 'GET',
        url:"/api/v1/ajax/generate_thumbnail/?id="+id,
        cache: false,
        success: function(returnval) {
            location.reload();
        },
    });
}