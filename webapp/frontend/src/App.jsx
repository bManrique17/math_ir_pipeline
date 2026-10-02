import { Route, Routes } from "react-router-dom";

import { fetchGoldFormulaGraph } from "./api";

import FormulaGraphPage from "./components/FormulaGraphPage";
import FormulaListView from "./components/FormulaListView";
import MultimodalRetrievalView from "./components/MultimodalRetrievalView";
import PostListView from "./components/PostListView";
import RetrievalView from "./components/RetrievalView";
import TopBar from "./components/TopBar";
import VocabView from "./components/VocabView";

export default function App() {
  return (
    <>
      <TopBar />
      <Routes>
        <Route path="/" element={<PostListView />} />
        <Route path="/formulas" element={<FormulaListView />} />
        <Route path="/formula/:id" element={<FormulaGraphPage />} />
        <Route
          path="/gold_formula/:id"
          element={<FormulaGraphPage fetchGraph={fetchGoldFormulaGraph} titlePrefix="Gold formula" />}
        />
        <Route path="/vocab" element={<VocabView />} />
        <Route path="/retrieval" element={<RetrievalView />} />
        <Route path="/multimodal_retrieval" element={<MultimodalRetrievalView />} />
      </Routes>
    </>
  );
}
