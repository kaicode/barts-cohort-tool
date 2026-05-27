import './App.css';
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import { Button, Form, Spinner } from "react-bootstrap";
import SnomedSearch from "./components/SnomedSearch";
import logo from './assets/Barts_logo.svg';

import { ethnicityOptions, genderOptions, defaultAgeRange } from './config/formOptions';

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, ResponsiveContainer
} from 'recharts';

// --- Cohort Form Page ---
function CohortForm() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const titleRegex = /^[a-zA-Z0-9 _-]+$/;
  const isTitleValid =
    title.trim().length > 4 && titleRegex.test(title);
    
  // Email: standard email validation (simple & safe)
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const isEmailValid =
    email.trim().length > 0 && emailRegex.test(email); 
  const [selectedGenders, setSelectedGenders] = useState([]);
  const [minAge, setMinAge] = useState(defaultAgeRange.min);
  const [maxAge, setMaxAge] = useState(defaultAgeRange.max);
  const [ethnicity, setEthnicity] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [mustHaveFindings, setMustHaveFindings] = useState([]);
  const [mustNotHaveFindings, setMustNotHaveFindings] = useState([]);
  const [includeChildCodesHave, setIncludeChildCodesHave] = useState(true);
  const [includeChildCodesNotHave, setIncludeChildCodesNotHave] = useState(true);
  const [loading, setLoading] = useState(false);
    
  
  
  useEffect(() => {
    document.title = "Patient Cohorting Tool";
  }, []);

  const handleEthnicityChange = (code, label) => {
    setEthnicity(prev => {
      const ethnicityItem = { code, display: label };
      return prev.some(item => item.code === code) ? prev.filter(item => item.code !== code) : [...prev, ethnicityItem];
    });
  };

  const handleGenderChange = (code, label) => {
    setSelectedGenders(prev => {
      const genderItem = { code, display: label };
      return prev.some(item => item.code === code) ? prev.filter(item => item.code !== code) : [...prev, genderItem];
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitted(true);
    setLoading(true);

    // Helper: keep only the main code if child codes not included
  const processFindings = (findings, includeChildren) => {
  return findings.map(item => {
    if (includeChildren) {
      // keep full object as-is
      return item;
    } else {
      // keep the original structure, but only the main code in codesWithDetails
      const mainCode = Array.isArray(item.code) ? item.code[0] : item.code;
      return {
        ...item,
        count: item.count, // keep the original count
        codesWithDetails: mainCode
          ? [{ code: mainCode.code, display: mainCode.display, count: 1 }]
          : [],
      };
    }
  });
};

  const cohortDefinition = {
    title,
    email,
    gender: selectedGenders.length === 0 ? "ALL" : selectedGenders,
    ageRange: { min: minAge, max: maxAge },
    ethnicity: ethnicity.length === 0 ? "ALL" : ethnicity,
    timeRange: {
      ...(startDate && { start: startDate }),
      ...(endDate && { end: endDate }),
    },
    mustHaveFindings: processFindings(mustHaveFindings, includeChildCodesHave),
    mustNotHaveFindings: processFindings(mustNotHaveFindings, includeChildCodesNotHave),
  };
  
  // console.log("Submitting cohortDefinition:", JSON.stringify(cohortDefinition, null, 2));


    try {
      const response = await fetch('/api/cohort/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cohortDefinition)
      });

      if (!response.ok) throw new Error('Network response was not ok');
      // const data = await response.json();

      // Save results and cohort title
      // sessionStorage.setItem("resultsData", JSON.stringify(data));
      // sessionStorage.setItem("cohortTitle", title);
      // window.open("/results", "_blank");
      console.log("Setting submitted to true");
      setSubmitted(true);
      

    } catch (error) {
      console.error('Error:', error);
      alert("There was an error processing your request.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
    <div style={{ position: "fixed", top: "20px", right: "20px", zIndex: 1000 }}>
      <img
        src={logo}
        alt="Logo"
        style={{  width: "15vw", minWidth: "80px", maxWidth: "250px", height: "auto" }}
    
      />
    </div>
    
    <div style={{ margin: '20px', maxWidth: '600px' }}>  
      {submitted ? (
        <div
          style={{
            marginTop: '60px',
            padding: '30px',             // increased from 20px
            display: 'block',            // make it take full width
            maxWidth: '800px',           // optional: set a max width
            width: '100%',               // fill available space up to maxWidth
            border: '1px solid #b6d4fe',
            backgroundColor: '#e7f3ff',
            borderRadius: '8px',         // slightly bigger rounded corners
            color: '#084298',
            boxSizing: 'border-box',     // ensures padding is included in width
          }}
        >
          <h2>Submission received.</h2>
          <p>The results will be sent to the email address provided when ready.</p>

         <p>
          If you have any issues, feedback, or comments, please email <br />
          the Barts Life Sciences data science team at<br />  
          <a href="mailto:bartshealth.bls.cohortingtool@nhs.net">bartshealth.bls.cohortingtool@nhs.net</a>
          </p>
          <p>
            You can now close this page.
          </p>
        </div>
        
      ) : (
        <div>
          <h1>Cohort Builder</h1>
          <p>Use this form to create a cohort by defining the selection criteria. </p>
          <p>
            If you have any issues, feedback, or comments, please email the Barts Life Sciences team at&nbsp;  
            <a href="mailto:bartshealth.bls.cohortingtool@nhs.net">bartshealth.bls.cohortingtool@nhs.net</a>
          </p>
          <Form onSubmit={handleSubmit} style={{ textAlign: 'left', marginTop: '20px' }}>
            <Form.Group className="mb-3" controlId="title">
              <Form.Label style={{ marginBottom: "1px" }}>Cohort Title (Required)</Form.Label>
            
              {/* Static helper text above the input */}
              <Form.Text className="text-muted" style={{ fontSize: "0.85em", display: "block", marginTop: "0.1px", marginBottom: "5px" }}>
                Title must be at least 5 characters. <br />
                Only letters, numbers, spaces, hyphens (-) and underscores (_). 
              </Form.Text>
            
              <Form.Control
                type="text"
                placeholder="Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                isInvalid={title.length > 0 && !isTitleValid}
              />
            
              {/* Dynamic error below the input */}
              <Form.Control.Feedback type="invalid" style={{ marginTop: "2px", whiteSpace: "pre-line" }}>
                {title.trim().length > 0 && title.trim().length < 5
                  ? "Title must be at least 5 characters."
                  : "Only letters, numbers, spaces, hyphens (-) and underscores (_) are allowed."}
              </Form.Control.Feedback>
            </Form.Group>
            
            <Form.Group className="mb-3" controlId="email">
              <Form.Label style={{ marginBottom: "1px" }}>Email address (Required)</Form.Label>
            
              {/* Helper text */}
              <Form.Text className="text-muted" style={{ fontSize: "0.85em", display: "block", marginTop: "0.5px", marginBottom: "5px" }}>
                The results will be sent to the email address provided once ready.
              </Form.Text>
            
              <Form.Control
                type="email"
                placeholder="name.surname@nhs.net"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                isInvalid={email.length > 0 && !isEmailValid}
              />
            
              {/* Validation feedback */}
              <Form.Control.Feedback type="invalid" style={{ marginTop: "2px" }}>
                Please enter a valid email address.
              </Form.Control.Feedback>
            </Form.Group>


            <Form.Group className="mb-3" controlId="gender">
              <Form.Label>Gender (Optional — if none selected, all categories will be considered)</Form.Label>
              {genderOptions.map(({ code, label }) => (
                <Form.Check
                  key={code}
                  type="checkbox"
                  label={label}
                  checked={selectedGenders.some(item => item.code === code)}
                  onChange={() => handleGenderChange(code, label)}
                />
              ))}
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Minimum Age: {minAge}</Form.Label>
              <Form.Range min={0} max={120} value={minAge} onChange={(e) => setMinAge(Number(e.target.value))} />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Maximum Age: {maxAge}</Form.Label>
              <Form.Range min={0} max={120} value={maxAge} onChange={(e) => setMaxAge(Number(e.target.value))} />
            </Form.Group>

            <Form.Group className="mb-3" controlId="ethnicity">
              <Form.Label>Ethnicity (Optional — if none selected, all categories will be considered)</Form.Label>
              {ethnicityOptions.map(({ code, label }) => (
                <Form.Check
                  key={code}
                  type="checkbox"
                  label={label}
                  checked={ethnicity.some(item => item.code === code)}
                  onChange={() => handleEthnicityChange(code, label)}
                />
              ))}
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Admission Time Range (Optional) </Form.Label>
              <Form.Control type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              <Form.Control type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ marginTop: "5px" }} />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Must HAVE Finding / Disorder (Optional)</Form.Label>
              <SnomedSearch
                label=""
                target_code="404684003"
                onSelect={(snomedSelection) => {
                  const newCode = snomedSelection.code.code || snomedSelection.code[0]?.code;
                  setMustHaveFindings((prev) =>
                    prev.some(item => (item.code.code || item.code[0]?.code) === newCode)
                      ? prev
                      : [...prev, snomedSelection]
                  );
                }}
              />
              {/*
              <Form.Check
                type="checkbox"
                label="Include child codes (subsumed concepts)"
                checked={includeChildCodesHave}
                onChange={() => setIncludeChildCodesHave(!includeChildCodesHave)}
                style={{ marginTop: "10px" }}
              />
              */}

              {mustHaveFindings.length > 0 && (
                <ul style={{ marginTop: "10px", paddingLeft: "20px" }}>
                  {mustHaveFindings.map((item, index) => {
                    const displayValue = item.code?.[0]?.display;
                    const uniqueId = item.code?.[0]?.code;
                    const count = includeChildCodesHave ? item.count : 1;

                    return (
                      <li key={uniqueId}>
                        <a
                          href={`https://termbrowser.nhs.uk/?perspective=full&conceptId1=${uniqueId}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ textDecoration: "underline", color: "#007bff" }}
                        >
                          {displayValue}
                        </a>{' '}
                        {`(Include ${count} code${count !== 1 ? 's' : ''})`}
                        <Button
                          variant="outline-danger"
                          size="sm"
                          onClick={() => setMustHaveFindings(prev => prev.filter((_, i) => i !== index))}
                          style={{ marginLeft: "10px", padding: "0 6px" }}
                        >
                          ❌
                        </Button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Must NOT HAVE Finding / Disorder (Optional)</Form.Label>
              <SnomedSearch
                label=""
                target_code="404684003"
                onSelect={(snomedSelection) => {
                  const newCode = snomedSelection.code.code || snomedSelection.code[0]?.code;
                  setMustNotHaveFindings((prev) =>
                    prev.some(item => (item.code.code || item.code[0]?.code) === newCode)
                      ? prev
                      : [...prev, snomedSelection]
                  );
                }}
              />
              
              {/*
              <Form.Check
                type="checkbox"
                label="Include child codes (subsumed concepts)"
                checked={includeChildCodesNotHave}
                onChange={() => setIncludeChildCodesNotHave(!includeChildCodesNotHave)}
                style={{ marginTop: "10px" }}
              />
              */}

              {mustNotHaveFindings.length > 0 && (
                <ul style={{ marginTop: "10px", paddingLeft: "20px" }}>
                  {mustNotHaveFindings.map((item, index) => {
                    const displayValue = item.code?.[0]?.display;
                    const uniqueId = item.code?.[0]?.code;
                    const count = includeChildCodesNotHave ? item.count : 1;

                    return (
                      <li key={uniqueId}>
                        <a
                          href={`https://termbrowser.nhs.uk/?perspective=full&conceptId1=${uniqueId}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ textDecoration: "underline", color: "#007bff" }}
                        >
                          {displayValue}
                        </a>{' '}
                        {`(Include ${count} code${count !== 1 ? 's' : ''})`}
                        <Button
                          variant="outline-danger"
                          size="sm"
                          onClick={() => setMustNotHaveFindings(prev => prev.filter((_, i) => i !== index))}
                          style={{ marginLeft: "10px", padding: "0 6px" }}
                        >
                          ❌
                        </Button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Form.Group>

            <Button
              variant="primary"
              disabled={!isTitleValid || !isEmailValid || loading}         
              onClick={handleSubmit}
            >
              {loading ? <Spinner size="sm" /> : "Submit"}
            </Button>
            <div style={{ fontSize: "0.85rem", color: "#6c757d", marginTop: "5px" }}>
              Please provide a title and a valid email address.
            </div>
          </Form>
      
          <h5 style={{ marginTop: '25px' }}>Summary of Selected Criteria</h5>
          <ul>
            <li><strong>Title:</strong> {title || "N/A"}</li>
            <li><strong>Email:</strong> {email || "N/A"}</li>
            <li><strong>Genders:</strong> {selectedGenders.length === 0 ? "All" : selectedGenders.map((item) => item.display).join(", ")}</li>
            <li><strong>Age Range:</strong> {minAge} - {maxAge}</li>
            <li><strong>Ethnicities:</strong> {ethnicity.length === 0 ? "All" : ethnicity.map((item) => item.display).join(", ")}</li>
            <li><strong>Admission Time Range:</strong> {startDate || endDate ? `${startDate || "Any"} to ${endDate || "Any"}` : "Any"}</li>
            <li><strong>Must Have Findings/Disorders:</strong> {mustHaveFindings.length === 0 ? "None" : mustHaveFindings.map((item) => (item.code && item.code[0] ? item.code[0].display : null)).filter(Boolean).join(", ") || "None"}</li>
            <li><strong>Must Not Have Findings/Disorders:</strong> {mustNotHaveFindings.length === 0 ? "None" : mustNotHaveFindings.map((item) => (item.code && item.code[0] ? item.code[0].display : null)).filter(Boolean).join(", ") || "None"}</li>
          </ul>
        </div>
    )}
    </div>
    </>
  );
}


// --- Results Page ---

 function ResultsPage() {
   const savedResults = sessionStorage.getItem("resultsData");
   const results = savedResults ? JSON.parse(savedResults) : null;
 
   if (!results) return <p>No results to display.</p>;
 
   const genderData = results.genderCounts || [];
   const ageData = results.ageGroups || [];
   const ethnicityData = results.ethnicityCounts || [];
   const topDiagnoses = results.topDiagnoses || [];
 
   const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AA336A'];
 
   return (
     <div style={{ margin: '20px', maxWidth: '900px' }}>
       <h1>Results for {results.title || "Untitled"}</h1>
     
       {/* Cohort Summary */}
       <div style={{ marginBottom: '20px' }}>
         <h4>Cohort Summary</h4>
         <p style={{ marginTop: '10px' }}>Total Patients: {results.total_patients || 0}</p>
         {!results.total_patients && (
           <p style={{ color: "red", fontStyle: "italic" }}>No results to display</p>
         )}        
       </div>
     
       {/* Only show charts if patients exist */}
       {results.total_patients > 0 && (
         <>
           {/* <p>Unique Diagnoses: {results.uniqueDiagnoses || 0}</p> */}
           {/* <p>Age Range: {results.minAge || '-'} - {results.maxAge || '-'}</p> */} 
             
           {/* Gender Distribution */}
           <h3>Gender Distribution</h3>
           <ResponsiveContainer width="100%" height={300}>
             <BarChart data={genderData}>
               <CartesianGrid strokeDasharray="3 3" />
               <XAxis dataKey="gender" />
               <YAxis />
               <Tooltip />
               <Legend />
               <Bar dataKey="count" fill="#8884d8" />
             </BarChart>
           </ResponsiveContainer>
     
           {/* Age Distribution */}
           <h3>Age Distribution</h3>
           <ResponsiveContainer width="100%" height={300}>
             <BarChart data={ageData}>
               <CartesianGrid strokeDasharray="3 3" />
               <XAxis dataKey="range" />
               <YAxis />
               <Tooltip />
               <Legend />
               <Bar dataKey="count" fill="#82ca9d" />
             </BarChart>
           </ResponsiveContainer>
     
           {/* Ethnicity Distribution */}
           <h3 style={{ marginBottom: '20px' }}>Ethnicity Distribution</h3>
           <div style={{ display: "flex", justifyContent: "center", marginBottom: "40px" }}>
             <PieChart width={600} height={350}>
               <Pie
                 data={ethnicityData}
                 dataKey="count"
                 nameKey="ethnicity"
                 cx="50%"
                 cy="55%"
                 outerRadius={120}
                 fill="#8884d8"
                 label
               >
                 {ethnicityData.map((entry, index) => (
                   <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                 ))}
               </Pie>
               <Tooltip />
               <Legend verticalAlign="bottom" height={36} />
             </PieChart>
           </div>
 
           {/* Raw JSON (commented out) */}
           {/*
           <section>
             <h3>Raw Data (JSON)</h3>
             <pre>{JSON.stringify(results, null, 2)}</pre>
           </section>
           */}
         </>
       )}
     </div>
   )}


// --- App with Router ---
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<CohortForm />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
    </Router>
  );
}

export default App;
