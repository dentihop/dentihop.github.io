// If cookie "navig" is set, use it in the link on main picture
function navig_mode(){
    var cookies = document.cookie.split(";"),
        key,
        value

    for(const cookie of cookies){
        [key, value] = cookie.split("=")
        if(key == "navig"){
            return value
        }
    }
}