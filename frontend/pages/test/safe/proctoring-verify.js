// /pages/test/proctoring-verify.js

import ProctoringSetup from "./proctoring-setup";

export default ProctoringSetup;

useEffect(() => {
  if (status) {
    const timeout = setTimeout(() => setStatus(""), 30000); // 5 seconds
    return () => clearTimeout(timeout);
  }
}, [status]);
