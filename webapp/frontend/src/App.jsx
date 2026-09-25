import { Route, Routes } from "react-router-dom";

import FormulaGraphPage from "./components/FormulaGraphPage";
import FormulaListView from "./components/FormulaListView";
import PostListView from "./components/PostListView";
import TopBar from "./components/TopBar";

export default function App() {
  return (
    <>
      <TopBar />
      <Routes>
        <Route path="/" element={<PostListView />} />
        <Route path="/formulas" element={<FormulaListView />} />
        <Route path="/formula/:id" element={<FormulaGraphPage />} />
      </Routes>
    </>
  );
}
