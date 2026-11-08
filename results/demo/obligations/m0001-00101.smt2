(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(declare-fun i_9 () (_ BitVec 8))
(declare-fun s_6 () (Array (_ BitVec 4) (_ BitVec 8)))
(assert
 (let ((?x21 (ite (= (_ bv42 8) (select (store s_6 i_8 i_9) i_8)) (_ bv1 1) (_ bv0 1))))
 (not (= (bvnot ?x21) (_ bv1 1)))))
(assert
 (let (($x79 (bvsge i_8 (_ bv15 4))))
(not $x79)))
(check-sat)
