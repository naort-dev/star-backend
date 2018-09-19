$(document).ready(function(){
if ($("#bookingadminadd_form").length)
{
    alert('This page is strictly for creating booking with provision to upload videos')

    if (!$("#id_request_transaction-0-source_id").val())
    {
        $("#id_request_transaction-0-source_id").val('src_1CYlA5ECTOB5aCAKr80zmtVQ');
        $("#id_request_transaction-0-source_id").attr('readonly', true);
    }
    if(!$('#id_request_transaction-0-stripe_transaction_id').val())
    {
        $('#id_request_transaction-0-stripe_transaction_id').val('ch_1CoTy3ECTOB5aCAKINgwD4P4');
        $("#id_request_transaction-0-stripe_transaction_id").attr('readonly', true);
    }

    if (!$('#id_request_transaction-0-amount').val())
    {
        $('#id_request_transaction-0-amount').val('0');
        $("#id_request_transaction-0-amount").attr('readonly', true);
    }

    if (1 == $('#id_request_transaction-0-transaction_status option:selected').val())
    {
        $('#id_request_transaction-0-transaction_status').val('3');
    }
}
$('#BookingId').click(function(){
    booking_id = $(this).attr('booking_id');
    $.ajax({
        type: 'GET',
        url:"/api/v1/ajax/process_booking/?booking="+booking_id,
        cache       : false,
        contentType : false,
        processData : false,
        success: function(returnval) {
            alert(returnval);
            window.location ='/admin';
         }
    });
});

});