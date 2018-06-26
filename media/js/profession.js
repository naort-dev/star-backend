$(document).ready(function(){
    $('form').submit(function (event) {
     var profession_1 = $("#id_celebrity_profession-0-profession option:selected").val();
        var profession_2 = $("#id_celebrity_profession-1-profession option:selected").val();
        var profession_3 = $("#id_celebrity_profession-2-profession option:selected").val();

        if(profession_1 == '' && profession_2 == '' && profession_3 == ''){
            alert("Please select one profession to continue");
            event.preventDefault();
        }
    });
});