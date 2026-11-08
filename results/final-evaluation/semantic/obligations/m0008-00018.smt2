(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 1))
(declare-fun s_3 () (_ BitVec 1))
(declare-fun s_11 () (_ BitVec 1))
(assert
 (let ((?x1253 (bvnot s_11)))
 (let ((?x1828 (bvor ?x1253 (bvnot (ite (= s_3 s_4) (_ bv1 1) (_ bv0 1))))))
 (and (= ?x1828 (_ bv1 1))))))
(assert
 (let (($x6963 (= s_3 s_4)))
(let ((?x508 (ite $x6963 (_ bv1 1) (_ bv0 1))))
(let ((?x1253 (bvnot s_11)))
(let ((?x1828 (bvor ?x1253 (bvnot ?x508))))
(let (($x1011 (= ?x1828 ?x508)))
(not $x1011)))))))
(check-sat)
