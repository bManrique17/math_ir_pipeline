import FormulaTable from "./FormulaTable";
import PostText from "./PostText";

export default function PostRow({ post }) {
  return (
    <div className="card mb-4">
      <div className="card-header">
        <strong>silver_id: {post.silver_id}</strong>
      </div>
      <div className="row g-0">
        <div className="col-md-5 p-3 border-end">
          <h6 className="text-uppercase text-muted small">Post</h6>
          <PostText content={post.content} />
        </div>
        <div className="col-md-7 p-3">
          <h6 className="text-uppercase text-muted small">Formulas</h6>
          <FormulaTable formulas={post.formulas} descriptors={post.descriptors} />
        </div>
      </div>
    </div>
  );
}
