(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(declare-fun s_11 () (Array (_ BitVec 8) (_ BitVec 32)))
(assert
 (let ((?x1034 (ite (bvult (select s_11 i_6) ((_ zero_extend 24) (_ bv200 8))) (_ bv1 1) (_ bv0 1))))
 (let ((?x16 (bvnot ?x1034)))
 (let ((?x536 (bvand (_ bv1 1) ?x16)))
 (not (= ?x536 (_ bv1 1)))))))
(assert
 (let ((?x249 (select s_11 i_6)))
(let ((?x159 ((_ extract 7 0) ?x249)))
(let (($x2829 (bvule (_ bv200 8) ?x159)))
(let (($x355 (or (not (= ((_ extract 31 8) ?x249) (_ bv0 24))) $x2829)))
(let (($x1343 (not $x355)))
(let (($x1877 (not $x1343)))
(not $x1877))))))))
(check-sat)
