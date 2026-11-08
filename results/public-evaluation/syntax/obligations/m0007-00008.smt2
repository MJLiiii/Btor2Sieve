(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 2))
(declare-fun s_6 () (_ BitVec 2))
(assert
 (let ((?x45 (ite (= (_ bv3 2) s_7) (_ bv1 1) (_ bv0 1))))
 (let ((?x64 (ite (= (_ bv3 2) s_6) (_ bv1 1) (_ bv0 1))))
 (let ((?x300 (bvand ?x64 ?x45)))
 (not (= ?x300 (_ bv1 1)))))))
(assert
 (let ((?x64 (ite (= (_ bv3 2) s_6) (_ bv1 1) (_ bv0 1))))
(let ((?x45 (ite (= (_ bv3 2) s_7) (_ bv1 1) (_ bv0 1))))
(let ((?x300 (bvand ?x64 ?x45)))
(let (($x68 (and (distinct ?x300 ?x64) true)))
(not $x68))))))
(check-sat)
