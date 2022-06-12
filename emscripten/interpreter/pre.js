const nodefs = require('fs')

function runPython(string){
    let ptr = Module.stringToNewUTF8(string);
    let result = Module._PyRun_SimpleString(ptr);
    Module._free(ptr);
    return result;
}

Module.postRun = function() {
    const test_code = nodefs.readFileSync("test.py", {encoding : "utf8"});
    FS.mkdir('/package_dir');
    FS.mount(NODEFS, { root: process.argv[2] }, '/package_dir');
    let errcode = runPython(test_code);
    process.exit(errcode);
    
}