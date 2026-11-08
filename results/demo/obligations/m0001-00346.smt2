(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(declare-fun s_6 () (Array (_ BitVec 4) (_ BitVec 8)))
(declare-fun i_9 () (_ BitVec 8))
(assert
 (not (= (bvnot (ite (= (_ bv42 8) (select s_6 i_8)) (_ bv1 1) (_ bv0 1))) (_ bv1 1))))
(assert
 (let ((?x50 (store s_6 i_8 i_9)))
(let ((?x168 (select ?x50 i_8)))
(let (($x156 (and (distinct ?x168 (_ bv127 8)) true)))
(not $x156)))))
(check-sat)
