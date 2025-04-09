const ethnicityOptions = [
  { code: "A", label: "White - British" },
  { code: "B", label: "White - Irish" },
  { code: "C", label: "White - Any other White background" },
  { code: "D", label: "Mixed - White and Black Caribbean" },
  { code: "E", label: "Mixed - White and Black African" },
  { code: "F", label: "Mixed - White and Asian" },
  { code: "G", label: "Mixed - Any other mixed background" },
  { code: "H", label: "Asian or Asian British - Indian" },
  { code: "J", label: "Asian or Asian British - Pakistani" },
  { code: "K", label: "Asian or Asian British - Bangladeshi" },
  { code: "L", label: "Asian or Asian British - Any other Asian background" },
  { code: "M", label: "Black or Black British - Caribbean" },
  { code: "N", label: "Black or Black British - African" },
  { code: "P", label: "Black or Black British - Any other Black background" },
  { code: "R", label: "Other Ethnic Groups - Chinese" },
  { code: "S", label: "Other Ethnic Groups - Any other ethnic group" },
  { code: "Z", label: "Not stated" },
  { code: "99", label: "Not known" },
];

const genderOptions = [
  { code: "1", label: "Male" },
  { code: "2", label: "Female" },
  { code: "3", label: "Non-binary" },
  { code: "4", label: "Other (not listed)" },
  { code: "X", label: "Not Known (not recorded)" },
  { code: "Z", label: "Not Stated (person asked but declined to provide a response)" },
];

const defaultAgeRange = {
  min: 18,
  max: 80
};

export { ethnicityOptions, genderOptions, defaultAgeRange };
